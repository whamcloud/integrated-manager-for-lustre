mod confirm_action_modal;

use crate::{
    components::{attrs, dropdown, font_awesome, modal, tooltip, Placement},
    generated::css_classes::C,
    sleep::sleep_with_handle,
    GMsg, MergeAttrs as _, RequestExt, WatchState,
};
use futures::channel::oneshot;
use iml_wire_types::{
    warp_drive::{ArcCache, ErasedRecord, Locks},
    ApiList, AvailableAction, CompositeId, LockChange,
};
use seed::{prelude::*, *};
use serde_json::json;
use std::{collections::BTreeMap, iter, sync::Arc, time::Duration};

type ActionMap = BTreeMap<String, Vec<(Arc<AvailableAction>, Box<Arc<dyn ErasedRecord>>)>>;

type AvailableActions = ApiList<AvailableAction>;

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct DryRun {
    pub dependency_jobs: Vec<Job>,
    pub transition_job: Job,
}

#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct Job {
    pub class: String,
    pub confirmation_prompt: Option<String>,
    pub description: String,
    pub requires_confirmation: bool,
    pub stateful_object_content_type_id: i64,
    pub stateful_object_id: i64,
}

pub fn composite_ids_to_query_string(xs: &[CompositeId]) -> String {
    xs.iter()
        .map(|x| format!("composite_ids={}", x))
        .collect::<Vec<String>>()
        .join("&")
}

fn locked_items<'a>(locks: &'a Locks, composite_ids: &'a [CompositeId]) -> impl Iterator<Item = &'a LockChange> {
    composite_ids
        .iter()
        .filter_map(move |x| locks.get(&x.to_string()))
        .flatten()
}

fn has_locks(locks: &Locks, composite_ids: &[CompositeId]) -> bool {
    locked_items(&locks, &composite_ids).next().is_some()
}

#[derive(Clone)]
pub struct IdMsg(pub u32, pub Msg);

pub enum State {
    Inactive,
    Activating,
    Active,
    Confirming(confirm_action_modal::Action),
}

impl Default for State {
    fn default() -> Self {
        Self::Inactive
    }
}

impl State {
    fn is_inactive(&self) -> bool {
        match self {
            Self::Inactive => true,
            _ => false,
        }
    }
}

#[derive(Default)]
pub struct Model {
    pub state: State,
    pub composite_ids: Vec<CompositeId>,
    pub request_controller: Option<fetch::RequestController>,
    pub actions: ActionMap,
    pub watching: WatchState,
    pub cancel: Option<oneshot::Sender<()>>,
    pub confirm_modal: confirm_action_modal::Model,
}

impl Model {
    pub fn new(composite_ids: Vec<CompositeId>) -> Self {
        Self {
            state: State::default(),
            composite_ids,
            request_controller: None,
            actions: BTreeMap::new(),
            watching: WatchState::default(),
            cancel: None,
            confirm_modal: confirm_action_modal::Model::default(),
        }
    }
    fn abort_request(&mut self) {
        self.cancel = None;

        if let Some(c) = self.request_controller.take() {
            c.abort();
        }
    }
}

impl Drop for Model {
    fn drop(&mut self) {
        self.abort_request();
    }
}

#[derive(Clone)]
pub enum Msg {
    StartFetch,
    SendFetch,
    WatchChange,
    Fetched(Box<fetch::ResponseDataResult<AvailableActions>>),
    ActionSelected(Arc<AvailableAction>, Arc<dyn ErasedRecord>),
    ConfirmJobModal(confirm_action_modal::Msg),
    DryRunSent(
        fetch::ResponseDataResult<DryRun>,
        Arc<AvailableAction>,
        Arc<dyn ErasedRecord>,
    ),
    Noop,
}

pub fn state_change(
    action: &Arc<AvailableAction>,
    erased_record: &Arc<dyn ErasedRecord>,
    dry_run: bool,
) -> fetch::Request {
    fetch::Request::api_item(erased_record.endpoint_name(), erased_record.id())
        .with_auth()
        .method(fetch::Method::Put)
        .send_json(&json!({ "state": action.state, "dry_run": dry_run }))
}

pub fn update(msg: IdMsg, cache: &ArcCache, model: &mut Model, orders: &mut impl Orders<IdMsg, GMsg>) {
    let IdMsg(id, msg) = msg;

    match msg {
        Msg::StartFetch => {
            if model.state.is_inactive() {
                model.state = State::Activating;
                orders.send_msg(IdMsg(id, Msg::SendFetch));
            }
        }
        Msg::SendFetch => {
            model.cancel = None;

            let request = fetch::Request::new(format!(
                "/api/action/?limit=0&{}",
                composite_ids_to_query_string(&model.composite_ids)
            ))
            .controller(|controller| model.request_controller = Some(controller));

            orders
                .skip()
                .perform_cmd(request.fetch_json_data(move |x| IdMsg(id, Msg::Fetched(Box::new(x)))));
        }
        Msg::Fetched(data_result) => {
            match *data_result {
                Ok(resp) => {
                    model.actions = group_actions_by_label(resp.objects.into_iter().map(Arc::new).collect(), &cache);
                }
                Err(fail_reason) => {
                    error!("An error has occurred {:?}", fail_reason);
                    orders.skip();
                }
            }

            let (cancel, fut) =
                sleep_with_handle(Duration::from_secs(10), IdMsg(id, Msg::SendFetch), IdMsg(id, Msg::Noop));

            model.cancel = Some(cancel);

            orders.perform_cmd(fut);

            if let State::Confirming(_) = model.state {
                return;
            }

            model.state = State::Active;
        }
        Msg::ActionSelected(x, y) => {
            model.abort_request();

            model.state = State::Confirming(confirm_action_modal::Action::Loading);

            if x.class_name.is_some() {
                if let Some(body) = &x.confirmation {
                    model.state = State::Confirming(confirm_action_modal::Action::Job(body.to_string(), x, y));
                }
            } else {
                let req = state_change(&x, &y, true);

                orders.perform_cmd(req.fetch_json_data(move |z| IdMsg(id, Msg::DryRunSent(z, x, y))));
            }
        }
        Msg::DryRunSent(data_result, action, erased_record) => match data_result {
            Ok(resp) => {
                model.state = State::Confirming(confirm_action_modal::Action::StateChange(resp, action, erased_record))
            }
            Err(fail_reason) => {
                error!("An error has occurred {:?}", fail_reason);
                orders.skip();
            }
        },
        Msg::ConfirmJobModal(msg) => {
            // Intercept the Close message to change dropdown state.
            if let confirm_action_modal::Msg::Modal(modal::Msg::Close) = msg {
                model.state = State::Active;
                orders.send_msg(IdMsg(id, Msg::SendFetch));

                return;
            }

            confirm_action_modal::update(
                msg,
                &mut model.confirm_modal,
                &mut orders.proxy(move |m| IdMsg(id, Msg::ConfirmJobModal(m))),
            );
        }
        Msg::WatchChange => model.watching.update(),
        Msg::Noop => {}
    };
}

fn group_actions_by_label<'a>(xs: Vec<Arc<AvailableAction>>, cache: &ArcCache) -> ActionMap {
    let mut x = xs.into_iter().fold(BTreeMap::new(), |mut x, action| {
        match cache.get_erased_record(&action.composite_id) {
            Some(r) => {
                let xs = x.entry(r.label().to_string()).or_insert_with(|| vec![]);

                xs.push((action, r));
            }
            None => {
                log!("Discarded action {:?} because it did not have an erased type", action);
            }
        };

        x
    });

    x.values_mut().for_each(|xs| sort_actions(xs));

    x
}

fn sort_actions<T>(actions: &mut Vec<(Arc<AvailableAction>, T)>) {
    actions.sort_by(|a, b| a.0.display_group.cmp(&b.0.display_group));
    actions.sort_by(|a, b| a.0.display_order.cmp(&b.0.display_order));
}

pub fn view(id: u32, model: &Model, all_locks: &Locks) -> Node<IdMsg> {
    let cls = class![
        C.bg_blue_500,
        C.hover__bg_blue_700,
        C.text_white,
        C.font_bold,
        C.py_2,
        C.px_4,
        C.rounded,
    ];

    let disabled_cls = class![C.opacity_50, C.cursor_not_allowed];

    if has_locks(all_locks, &model.composite_ids) {
        return span![
            attrs::container(),
            class![C.inline_block],
            button![
                cls,
                disabled_cls,
                "Locked",
                font_awesome(class![C.w_4, C.h_4, C.inline, C.ml_1, C.pulse], "spinner"),
            ],
            tooltip::view("This record has active locks. It cannot be modified.", Placement::Left),
        ];
    }

    match &model.state {
        State::Activating => button![
            cls.merge_attrs(disabled_cls),
            "Actions",
            font_awesome(class![C.w_4, C.h_4, C.inline, C.ml_1, C.pulse], "spinner"),
        ],
        State::Inactive => button![
            cls,
            "Actions",
            font_awesome(class![C.w_4, C.h_4, C.inline, C.ml_1], "chevron-down"),
            simple_ev(Ev::MouseMove, IdMsg(id, Msg::StartFetch))
        ],
        State::Active => {
            if model.actions.is_empty() {
                button![cls.merge_attrs(disabled_cls), "No Actions"]
            } else {
                span![
                    class![C.relative, C.inline_block],
                    button![
                        cls,
                        "Actions",
                        font_awesome(class![C.w_4, C.h_4, C.inline, C.ml_1], "chevron-down"),
                        simple_ev(Ev::Click, IdMsg(id, Msg::WatchChange))
                    ],
                    dropdown::wrapper_view(
                        class![C.z_30, C.w_64],
                        Placement::Bottom,
                        model.watching.is_open(),
                        items_view(id, &model.actions)
                    )
                ]
            }
        }
        State::Confirming(action) => div![
            button![
                cls.merge_attrs(disabled_cls),
                "Actions",
                font_awesome(class![C.w_4, C.h_4, C.inline, C.ml_1, C.pulse], "spinner"),
            ],
            confirm_action_modal::view(action).map_msg(move |x| IdMsg(id, Msg::ConfirmJobModal(x))),
        ],
    }
}

fn items_view(id: u32, x: &ActionMap) -> impl View<IdMsg> {
    let xs = x
        .into_iter()
        .flat_map(|(label, actions)| {
            let xs = actions.into_iter().map(|(y, z)| {
                let y2 = Arc::clone(&y);
                let z2 = Arc::clone(&z);

                div![
                    attrs::container(),
                    dropdown::item_view(a![y.verb]),
                    tooltip::view(&y.long_description, Placement::Left),
                    mouse_ev(Ev::Click, move |_| IdMsg(id, Msg::ActionSelected(y2, z2)))
                ]
            });

            iter::once(div![class![C.text_sm, C.pt_3, C.text_gray_800], label]).chain(xs)
        })
        .collect::<Vec<_>>();

    nodes![xs]
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_composite_ids_to_query_string() {
        let query_string = composite_ids_to_query_string(&[CompositeId(57, 3), CompositeId(49, 1)]);

        assert_eq!(query_string, "composite_ids=49:1&composite_ids=57:3");
    }
}
