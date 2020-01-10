use crate::{
    components::{dropdown, font_awesome, modal, tooltip, Placement},
    generated::css_classes::C,
    sleep::sleep_with_handle,
    GMsg, MergeAttrs as _, WatchState,
};
use futures::channel::oneshot;
use iml_wire_types::{ApiList, AvailableAction, CompositeId, Label, ToCompositeId};
use seed::{prelude::*, *};
use std::{sync::Arc, time::Duration};

pub type AvailableActions = ApiList<AvailableAction>;

pub trait ActionRecord: ToCompositeId + serde::Serialize + Label + Clone {}
impl<T: ToCompositeId + serde::Serialize + Label + Clone> ActionRecord for T {}

pub fn composite_ids_to_query_string(xs: &[CompositeId]) -> String {
    let mut xs: Vec<String> = xs
        .iter()
        .map(|x| format!("composite_ids={}", x))
        .collect::<Vec<String>>();

    xs.sort();
    xs.join("&")
}

#[derive(Clone)]
pub struct IdMsg(pub u32, pub Msg);

#[derive(PartialEq, Eq)]
pub enum State {
    Inactive,
    Activating,
    Active,
    Confirming(String, String),
}

impl Default for State {
    fn default() -> Self {
        Self::Inactive
    }
}

#[derive(Default)]
pub struct Model {
    pub state: State,
    pub composite_ids: Vec<CompositeId>,
    pub request_controller: Option<fetch::RequestController>,
    pub actions: Vec<Arc<AvailableAction>>,
    pub watching: WatchState,
    pub cancel: Option<oneshot::Sender<()>>,
    pub confirm_modal: modal::Model,
}

impl Model {
    pub fn new(composite_ids: Vec<CompositeId>) -> Self {
        Self {
            state: State::default(),
            composite_ids,
            request_controller: None,
            actions: vec![],
            watching: WatchState::default(),
            cancel: None,
            confirm_modal: modal::Model::default(),
        }
    }
}

impl Drop for Model {
    fn drop(&mut self) {
        self.cancel = None;

        if let Some(c) = self.request_controller.take() {
            c.abort();
        }
    }
}

#[derive(Clone)]
pub enum Msg {
    StartFetch,
    SendFetch,
    WatchChange,
    Fetched(Box<fetch::ResponseDataResult<AvailableActions>>),
    ActionSelected(Arc<AvailableAction>),
    ConfirmModal(modal::Msg),
    Noop,
}

pub fn update(msg: IdMsg, model: &mut Model, orders: &mut impl Orders<IdMsg, GMsg>) {
    let IdMsg(id, msg) = msg;

    match msg {
        Msg::StartFetch => {
            if model.state == State::Inactive {
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
                    model.actions = resp.objects.into_iter().map(Arc::new).collect();
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

            if let State::Confirming(_, _) = model.state {
                return;
            }

            model.state = State::Active;
        }
        Msg::ActionSelected(x) => {
            log!(x);

            if x.class_name.is_some() {
                if let Some(body) = &x.confirmation {
                    model.state = State::Confirming(x.verb.clone(), body.clone());
                }
            } else {
            }
        }
        Msg::ConfirmModal(msg) => modal::update(
            msg,
            &mut model.confirm_modal,
            &mut orders.proxy(move |m| IdMsg(id, Msg::ConfirmModal(m))),
        ),
        Msg::WatchChange => model.watching.update(),
        Msg::Noop => {}
    };
}

fn confirm_modal_view(id: u32, title: &str, body: &str) -> Node<IdMsg> {
    modal::bg_view(
        true,
        modal::content_view(vec![
            modal::title_view(span![title]),
            span![El::from_html(body)],
            modal::footer_view(vec![
                button![
                    class![
                        C.bg_transparent,
                        C.py_2,
                        C.px_4,
                        C.rounded_full,
                        C.text_blue_500,
                        C.hover__bg_gray_100,
                        C.hover__text_blue_400,
                        C.mr_2,
                    ],
                    "Confirm",
                ],
                button![
                    class![
                        C.bg_blue_500,
                        C.py_2,
                        C.px_4,
                        C.rounded_full,
                        C.text_white,
                        C.hover__bg_blue_400,
                    ],
                    "Cancel",
                ],
            ]),
        ]),
    )
    .map_msg(move |m| IdMsg(id, Msg::ConfirmModal(m)))
}

pub fn view(id: u32, model: &Model) -> Node<IdMsg> {
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
                        model
                            .actions
                            .iter()
                            .map(|x| {
                                let x2 = Arc::clone(x);
                                div![
                                    tooltip::container(),
                                    dropdown::item_view(a![x.verb,]),
                                    tooltip::view(&x.long_description, Placement::Left),
                                    mouse_ev(Ev::Click, move |_| IdMsg(id, Msg::ActionSelected(x2)))
                                ]
                            })
                            .collect::<Vec<_>>()
                    )
                ]
            }
        }
        State::Confirming(title, body) => div![
            button![
                cls.merge_attrs(disabled_cls),
                "Actions",
                font_awesome(class![C.w_4, C.h_4, C.inline, C.ml_1, C.pulse], "spinner"),
            ],
            confirm_modal_view(id, title, body),
        ],
    }
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
