use crate::{components::Placement, generated::css_classes::C};
use seed::{prelude::*, virtual_dom::Attrs, Style, *};

pub fn wrapper_view<T>(attrs: Attrs, placement: Placement, open: bool, children: impl View<T>) -> Node<T> {
    if !open {
        return empty![];
    }

    let st = match placement {
        Placement::Top => {
            style! {
                St::Transform => "translate(50%, -100%)",
                St::Top => 0,
                St::Right => percent(50),
                St::MarginTop => px(-10),
            }
        }
        Placement::Bottom => {
            style! {
                St::Transform => "translateX(50%)",
                St::Top => percent(100),
                St::Right => percent(50),
                St::MarginTop => px(3),
                St::PaddingTop => px(5)
            }
        }
        _ => Style::empty(),
    };

    let mut cls = class![
        C.mt_2,
        C.py_2,
        C.cursor_pointer,
        C.text_center,
        C.bg_white,
        C.rounded_lg,
        C.shadow_xl,
        C.absolute
    ];

    cls.merge(attrs);

    div![cls, st, children.els(),]
}

pub fn item_view<T>(children: impl View<T>) -> Node<T> {
    div![
        class![
            C.bg_gray_100,
            C.hover__bg_blue_700,
            C.hover__text_white,
            C.m_2,
            C.p_2,
            C.rounded,
            C.text_gray_800,
        ],
        children.els()
    ]
}
