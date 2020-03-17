use crate::components::table;
use crate::{
    components::{font_awesome, modal},
    extensions::{MergeAttrs, NodeExt},
    generated::css_classes::C,
    key_codes, sleep_with_handle, GMsg,
};
use futures::channel::oneshot;
use iml_wire_types::{ApiList, Command};
use seed::{prelude::*, *};
use std::time::Duration;

/// The component polls `/api/command` endpoint and this constant defines how often it does.
const POLL_INTERVAL: Duration = Duration::from_millis(1000);

#[derive(Default, Debug)]
pub struct Model {
    pub modal: modal::Model,
    pub commands: Vec<Command>,
    pub cancel: Option<oneshot::Sender<()>>,
}

/// `Msg::FireCommand(..)` adds the new command to the polling list
/// `Msg::Fetch` spawns a future to make the api call
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
        .map(|x| format!("id__in={}", x))
        .collect::<Vec<String>>()
        .join("&");
    // TODO make it paged instead of being unlimited
    let url = format!("/api/{}?{}&limit=0", Command::enpoint_name(), ids);
    Request::new(url).fetch_json_data(|x| Msg::Fetched(Box::new(x))).await
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Modal(msg) => {
            modal::update(msg, &mut model.modal, &mut orders.proxy(Msg::Modal));
        }
        Msg::FireCommand(cmd) => {
            // add the command to the list (if it isn't yet)
            // and start polling for the commands' status
            // use the (little) optimization: if the command
            let ids: Vec<u32> = model.commands.iter().map(|x| x.id).collect();
            let cmd_finished = cmd.complete || cmd.cancelled || cmd.errored;
            if !cmd_finished && !ids.contains(&cmd.id) {
                model.modal.open = true;
                model.commands.push(cmd);
                orders.send_msg(Msg::Fetch);
            }
        }
        Msg::Fetch => {
            log!("command_modal::Msg::Fetch");
            if !model.commands.is_empty() {
                let ids = model.commands.iter().map(|x| x.id).collect();
                orders.skip().perform_cmd(fetch_command_status(ids));
            }
        }
        Msg::Fetched(cmd_status_result) => {
            match *cmd_status_result {
                Ok(mut cmd_status) => {
                    model.commands = cmd_status
                        .objects
                        .into_iter()
                        .filter(|x| !x.complete && !x.cancelled && !x.errored)
                        .collect();
                    let ids: String = model
                        .commands
                        .iter()
                        .map(|x| x.id.to_string())
                        .collect::<Vec<_>>()
                        .join(", ");
                    log!("command_modal::Msg::Fetched:", ids);
                }
                Err(e) => {
                    error!("Failed to perform fetch_command_status {:#?}", e);
                    orders.skip();
                }
            }
            if !model.commands.is_empty() {
                let (cancel, fut) = sleep_with_handle(POLL_INTERVAL, Msg::Fetch, Msg::Noop);
                model.cancel = Some(cancel);
                orders.perform_cmd(fut);
            } else {
                orders.send_msg(Msg::Modal(modal::Msg::Close));
            }
        }
        Msg::Noop => {
            log!("command_modal::Msg::Noop");
        }
    }
}

pub(crate) fn view(model: &Model) -> Node<Msg> {
    modal::bg_view(
        model.modal.open,
        Msg::Modal,
        modal::content_view(
            Msg::Modal,
            vec![
                modal::title_view(Msg::Modal, span!["Executing the commands"]),
                div![
                    div![
                        class![C.my_12, C.text_center, C.text_gray_500],
                        font_awesome(class![C.w_12, C.h_12, C.inline, C.pulse], "spinner"),
                    ],
                    div!["Commands"],
                ],
                modal::footer_view(vec![close_button()]).merge_attrs(class![C.pt_8]),
            ],
        ),
    )
    .with_listener(keyboard_ev(Ev::KeyDown, move |ev| match ev.key_code() {
        key_codes::ESC => Msg::Modal(modal::Msg::Close),
        _ => Msg::Noop,
    }))
    .merge_attrs(class![C.text_black])
}

fn close_button() -> Node<Msg> {
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
        "Close",
    ]
    .map_msg(Msg::Modal)
}
