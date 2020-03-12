use crate::{
    components::{
        action_dropdown::{state_change, DryRun},
        font_awesome, modal,
    },
    extensions::{MergeAttrs, NodeExt},
    generated::css_classes::C,
    key_codes, GMsg, RequestExt,
};
use iml_wire_types::{warp_drive::ErasedRecord, AvailableAction, Command, EndpointName};
use seed::{prelude::*, *};

#[derive(Default, Debug)]
pub struct Model {
    pub modal: modal::Model,
}

#[derive(Clone, Debug)]
pub enum Msg {
    RunCommand,
    Modal(modal::Msg),
    Noop,
}

// #[derive(Debug)]
// pub enum Action {
//     Loading,
//     SendRunCommand,
//     RunCommandSent,
// }

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Modal(msg) => {
            modal::update(msg, &mut model.modal, &mut orders.proxy(Msg::Modal));
        }
        Msg::Noop => {}
        Msg::RunCommand => {
            log!("Msg::RunCommand");
        }
    }
}

pub(crate) fn view(model: &Model) -> Node<Msg> {
    let txt = if model.modal.open { "state = OPEN".to_string() } else { "state = CLOSED".to_string() };
    modal::bg_view(
        true,
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
                    div![
                        class![C.py_4, C.font_medium],
                        txt,
                    ],
                ],
                modal::footer_view(vec![cancel_button()]).merge_attrs(class![C.pt_8]),
            ],
        ),
    )
        // .with_listener(keyboard_ev(Ev::KeyDown, move |ev| match ev.key_code() {
        //     key_codes::ESC => Msg::Modal(modal::Msg::Close),
        //     _ => Msg::Noop,
        // }))
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
