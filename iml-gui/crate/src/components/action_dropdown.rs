use crate::{
    components::{dropdown, font_awesome, tooltip, Placement},
    generated::css_classes::C,
    WatchState,
};
use futures::{
    channel::oneshot,
    future::{self, Either},
    Future, FutureExt,
};
use gloo_timers::future::TimeoutFuture;
use iml_wire_types::{ApiList, AvailableAction, CompositeId, Label, ToCompositeId};
use seed::{prelude::*, *};

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
}

impl Default for State {
    fn default() -> Self {
        State::Inactive
    }
}

#[derive(Default)]
pub struct Model {
    pub state: State,
    pub composite_ids: Vec<CompositeId>,
    pub request_controller: Option<fetch::RequestController>,
    pub actions: Vec<AvailableAction>,
    pub watching: WatchState,
    pub cancel: Option<oneshot::Sender<()>>,
}

impl Model {
    pub fn new(composite_ids: Vec<CompositeId>) -> Self {
        Model {
            state: State::default(),
            composite_ids,
            request_controller: None,
            actions: vec![],
            watching: WatchState::default(),
            cancel: None,
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
    Fetched(fetch::ResponseDataResult<AvailableActions>),
    Noop,
}

pub fn update(msg: IdMsg, model: &mut Model, orders: &mut impl Orders<IdMsg>) {
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

            // FIXME: Need to figure out differing urls for dev / prod
            let request = fetch::Request::new(format!(
                "https://localhost:7444/api/action/?limit=0&{}",
                composite_ids_to_query_string(&model.composite_ids)
            ))
            .controller(|controller| model.request_controller = Some(controller));

            orders
                .skip()
                .perform_cmd(request.fetch_json_data(move |x| IdMsg(id, Msg::Fetched(x))));
        }
        Msg::Fetched(data_result) => {
            model.state = State::Active;

            match data_result {
                Ok(resp) => {
                    model.actions = resp.objects;
                }
                Err(fail_reason) => {
                    error!("An error has occurred {:?}", fail_reason);
                    orders.skip();
                }
            }

            let (cancel, fut) = fetch_after_delay(id);

            model.cancel = Some(cancel);

            orders.perform_cmd(fut);
        }
        Msg::WatchChange => model.watching.update(),
        Msg::Noop => {}
    };
}

pub fn fetch_after_delay(id: u32) -> (oneshot::Sender<()>, impl Future<Output = Result<IdMsg, IdMsg>>) {
    let (p, c) = oneshot::channel::<()>();

    let fut = future::select(c, TimeoutFuture::new(10_000)).map(move |either| match either {
        Either::Left((_, b)) => {
            drop(b);

            log!("fetch timeout dropped");

            Ok(IdMsg(id, Msg::Noop))
        }
        Either::Right((_, _)) => Ok(IdMsg(id, Msg::SendFetch)),
    });

    (p, fut)
}

pub fn view(id: u32, model: &Model) -> Node<IdMsg> {
    let mut el = button![
        class![
            C.bg_blue_500,
            C.hover__bg_blue_700,
            C.text_white,
            C.font_bold,
            C.py_2,
            C.px_4,
            C.rounded,
        ],
        match model.state {
            State::Activating => {
                vec![
                    Node::new_text("Waiting"),
                    font_awesome(class![C.w_4, C.h_4, C.inline, C.ml_1, C.pulse], "spinner"),
                ]
            }
            State::Inactive => {
                vec![
                    Node::new_text("Actions"),
                    font_awesome(class![C.w_4, C.h_4, C.inline, C.ml_1], "chevron-down"),
                ]
            }
            State::Active => {
                if model.actions.is_empty() {
                    vec![Node::new_text("No Actions")]
                } else {
                    vec![
                        Node::new_text("Actions"),
                        font_awesome(class![C.w_4, C.h_4, C.inline, C.ml_1], "chevron-down"),
                    ]
                }
            }
        }
    ];

    if model.state == State::Inactive {
        el.add_listener(simple_ev(Ev::MouseMove, IdMsg(id, Msg::StartFetch)));
    } else if !model.actions.is_empty() {
        el.add_listener(simple_ev(Ev::Click, IdMsg(id, Msg::WatchChange)));

        el = span![
            class![C.relative, C.inline_block],
            el,
            dropdown::wrapper_view(
                class![C.z_30, C.w_64],
                Placement::Bottom,
                model.watching.is_open(),
                model
                    .actions
                    .iter()
                    .map(|x| div![
                        tooltip::container(),
                        dropdown::item_view(a![x.verb,]),
                        tooltip::view(&x.long_description, Placement::Left)
                    ])
                    .collect::<Vec<_>>()
            )
        ];
    }

    el
}
