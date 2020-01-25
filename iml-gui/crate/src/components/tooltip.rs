use crate::{
    components::{arrow, Placement},
    generated::css_classes::C,
};
use seed::{prelude::*, virtual_dom::Attrs, *};

/// Call this fn within the element wrapping the tooltip
/// It will add the needed styles so the tooltip will render
/// in the expected position and will render on hover.
pub fn container() -> Attrs {
    class![C.relative, C.group, C.cursor_pointer]
}

/// Render a tooltip with vaild CSS color string.
pub(crate) fn color_view<T>(content: &str, placement: Placement, color: &str) -> Node<T> {
    let tooltip_top_styles = style! {
        St::Transform => "translate(50%, -100%)",
        St::Top => 0,
        St::Right => percent(50),
        St::MarginTop => px(-3),
    };

    let tooltip_right_styles = style! {
        St::Transform => "translateY(50%)",
        St::Left => percent(100),
        St::Bottom => percent(50),
        St::MarginLeft => px(8),
    };

    let tooltip_bottom_styles = style! {
        St::Transform => "translateX(50%)",
        St::Top => percent(100),
        St::Right => percent(50),
        St::MarginTop => px(3),
        St::PaddingTop => px(5)
    };

    let tooltip_left_styles = style! {
        St::Bottom => percent(50),
        St::Transform => "translate(calc(-100% - 8px),50%)",
    };

    let tooltip_style = match placement {
        Placement::Left => tooltip_left_styles,
        Placement::Right => tooltip_right_styles,
        Placement::Top => tooltip_top_styles,
        Placement::Bottom => tooltip_bottom_styles,
    };

    div![
        class![
            C.absolute,
            C.hidden,
            C.group_hover__block,
            C.pointer_events_none,
            C.z_20,
            C.whitespace_normal
        ],
        tooltip_style,
        arrow(placement, color),
        div![
            class![
                C.text_center,
                C.text_white,
                C.text_sm,
                C.py_1,
                C.px_3,
                C.rounded,
                C.opacity_90,
            ],
            style! {
                St::Width => px(150),
                St::BackgroundColor => color,
            },
            content
        ]
    ]
}

/// Render a tooltip.
pub(crate) fn view<T>(content: &str, direction: Placement) -> Node<T> {
    color_view(content, direction, "black")
}

/// Render a tooltip with a red error color.
#[allow(unused)]
pub(crate) fn error_view<T>(content: &str, direction: Placement) -> Node<T> {
    color_view(content, direction, "red")
}
