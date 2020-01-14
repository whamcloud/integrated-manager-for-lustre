use crate::{components::font_awesome, generated::css_classes::C, key_codes};
use seed::{prelude::*, *};

#[derive(Default)]
pub struct Model {
    pub open: bool,
}

#[derive(Clone)]
pub enum Msg {
    KeyDown(u32),
    Close,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg>) {
    match msg {
        Msg::KeyDown(code) => {
            if code == key_codes::ESC {
                orders.send_msg(Msg::Close);
            }
        }
        Msg::Close => {
            model.open = false;
        }
    }
}

pub fn title_view(children: impl View<Msg>) -> Node<Msg> {
    div![
        class![C.flex, C.justify_between, C.items_center, C.pb_3,],
        p![class![C.text_2xl, C.font_bold,], children.els()],
        div![
            class![C.cursor_pointer, C.z_50,],
            font_awesome(class![C.w_4, C.h_4, C.inline, C.ml_1], "times"),
            simple_ev(Ev::Click, Msg::Close)
        ],
    ]
}

pub fn footer_view<T>(children: impl View<T>) -> Node<T> {
    div![class![C.flex, C.justify_end, C.pt_2,], children.els()]
}

pub fn content_view(children: impl View<Msg>) -> Node<Msg> {
    div![
        class![
            C.bg_white,
            C.w_10of12,
            C.md__max_w_3xl,
            C.mx_auto,
            C.rounded,
            C.shadow_lg,
            C.z_50,
            C.overflow_y_auto,
        ],
        div![
            class![
                C.absolute,
                C.top_0,
                C.right_0,
                C.cursor_pointer,
                C.flex,
                C.flex_col,
                C.items_center,
                C.mt_4,
                C.mr_4,
                C.text_white,
                C.text_sm,
                C.z_50,
            ],
            simple_ev(Ev::Click, Msg::Close),
            font_awesome(class![C.w_4, C.h_4, C.inline], "times"),
            span![class![C.text_sm,], "(Esc)",],
        ],
        div![class![C.py_4, C.text_left, C.px_6,], children.els()]
    ]
}

pub fn bg_view(open: bool, children: impl View<Msg>) -> Node<Msg> {
    if !open {
        return empty![];
    }

    div![
        class![
            C.fixed,
            C.w_full,
            C.h_full,
            C.top_0,
            C.left_0,
            C.flex,
            C.items_center,
            C.justify_center,
        ],
        attrs! {At::TabIndex => 0, At::AutoFocus => true},
        keyboard_ev("keydown", |ev| Msg::KeyDown(ev.key_code())),
        div![
            class![C.absolute, C.w_full, C.h_full],
            style! {St::BackgroundColor => "rgba(26, 32, 44, 0.6)"},
            children.els()
        ],
    ]
}
