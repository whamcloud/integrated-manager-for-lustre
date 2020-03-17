use crate::{components::{
    font_awesome, modal,
}, extensions::{MergeAttrs, NodeExt}, generated::css_classes::C, key_codes, sleep_with_handle, GMsg};
use futures::channel::oneshot;
use iml_wire_types::{ApiList, Command};
use seed::{prelude::*, *};
use std::time::Duration;

/// The component polls `/api/command` endpoint and this constant defines how often it does.
const POLL_INTERVAL: Duration = Duration::from_millis(500);

#[derive(Default, Debug)]
pub struct Model {
    pub modal: modal::Model,
    pub executing_ids: Vec<u32>,
    pub cancel: Option<oneshot::Sender<()>>,
    pub counter: u32,
}

/// `Msg::Fetched(..)` wraps the result like
/// ```norun
/// {
///    "meta": {
///      "limit": 1000,
///      "next": null,
///      "offset": 0,
///      "previous": null,
///      "total_count": 10
///    },
///    "objects": [ cmd0, cmd1, ..., cmd9 ]
/// }
/// ```
#[derive(Clone, Debug)]
pub enum Msg {
    Modal(modal::Msg),
    FireCommand(Command),
    Fetch,
    Fetched(Box<seed::fetch::ResponseDataResult<ApiList<Command>>>),
    Noop,
}

async fn fetch_command_status(command_ids: Vec<u32>) -> Result<Msg, Msg> {
    // e.g. GET /api/command/?id__in=1&id__in=2&id__in=11&limit=0
    let ids = command_ids
        .iter()
        .map(|id| format!("id__in={}", id))
        .collect::<Vec<String>>()
        .join("&");
    // TODO make it paged instead of being unlimited
    let url = format!("/api/command?limit=0&{}", ids);
    Request::new(url).fetch_json_data(|x| Msg::Fetched(Box::new(x))).await
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Modal(msg) => {
            modal::update(msg, &mut model.modal, &mut orders.proxy(Msg::Modal));
        }
        Msg::FireCommand(cmd) => {
            log!("command_modal::Msg::FireCommand", cmd);
            if !model.executing_ids.contains(&cmd.id) {
                model.executing_ids.push(cmd.id);
                model.modal.open = true;
                orders.send_msg(Msg::Fetch);
            }
        }
        Msg::Fetch => {
            // log!("command_modal::Msg::Fetch");
            if !model.executing_ids.is_empty() {
                orders
                    .skip()
                    .perform_cmd(fetch_command_status(model.executing_ids.clone()));
            }
            model.counter = 0;
        }
        Msg::Fetched(cmd_status_result) => {
            match *cmd_status_result {
                Ok(cmd_status) => {
                    let cmd_status: ApiList<Command> = cmd_status;
                    // let result: Vec<(u32, bool, &str)> = cmd_status
                    //     .objects
                    //     .iter()
                    //     .map(|cmd| (cmd.id, cmd.complete, &cmd.message[..]))
                    //     .collect();
                    model.executing_ids = cmd_status
                        .objects
                        .iter()
                        .filter(|cmd| !cmd.complete)
                        .map(|cmd| cmd.id)
                        .collect();
                    // log!("command_modal::Msg::Fetched", result);
                }
                Err(e) => {
                    error!("Failed to perform fetch_command_status {:#?}", e);
                    orders.skip();
                }
            }
            if !model.executing_ids.is_empty() {
                let (cancel, fut) = sleep_with_handle(POLL_INTERVAL, Msg::Fetch, Msg::Noop);
                model.cancel = Some(cancel);
                orders.perform_cmd(fut);
            }
        }
        Msg::Noop => {
            log!("command_modal::Msg::Noop");
        }
    }
}

pub(crate) fn view(model: &Model) -> Node<Msg> {
    let open = model.modal.open;
    let txt = if open {
        "state = OPEN".to_string()
    } else {
        "state = CLOSED".to_string()
    };
    modal::bg_view(
        open,
        Msg::Modal,
        modal::content_view(
            Msg::Modal,
            vec![
                modal::title_view(Msg::Modal, span!["Executing the command"]),
                div![
                    div![
                        class![C.my_12, C.text_center, C.text_gray_500],
                        font_awesome(class![C.w_12, C.h_12, C.inline, C.pulse], "spinner"),
                    ],
                    div![class![C.py_4, C.font_medium], txt,],
                ],
                modal::footer_view(vec![cancel_button()]).merge_attrs(class![C.pt_8]),
            ],
        ),
    )
    .with_listener(keyboard_ev(Ev::KeyDown, move |ev| match ev.key_code() {
        key_codes::ESC => Msg::Modal(modal::Msg::Close),
        _ => Msg::Noop,
    }))
    .merge_attrs(class![C.text_black])
}

fn cancel_button() -> Node<Msg> {
    seed::button![
        class![
            C.bg_transparent,
            C.py_2,
            C.px_4,
            C.rounded_full,
            C.text_blue_500,
            C.hover__bg_gray_100,
            C.hover__text_blue_400,
        ],
        simple_ev(Ev::Click, modal::Msg::Close),
        "Cancel",
    ]
    .map_msg(Msg::Modal)
}
