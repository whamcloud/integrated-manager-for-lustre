use crate::generated::css_classes::C;
use seed::{dom_types::Attrs, prelude::*, *};

#[derive(Debug, Clone, Copy)]
pub enum TooltipPlacement {
    Left,
    Right,
    Top,
    Bottom,
}

impl From<&TooltipPlacement> for &str {
    fn from(p: &TooltipPlacement) -> Self {
        match p {
            TooltipPlacement::Left => "left",
            TooltipPlacement::Right => "right",
            TooltipPlacement::Top => "top",
            TooltipPlacement::Bottom => "bottom",
        }
    }
}

/// Call this fn within the element wrapping the tooltip
/// It will add the needed styles so the tooltip will render
/// in the expected position and will render on hover.
pub fn tooltip_container() -> Attrs {
    class![C.relative, C.group, C.cursor_pointer]
}

/// Render a tooltip with vaild CSS color string.
pub fn color_tooltip<T>(
    content: &str,
    direction: TooltipPlacement,
    color: &str,
) -> Node<T> {
    let arrow_top_styles = style! {
        St::Top => percent(100),
        St::Left => percent(50),
        St::MarginLeft => px(-5),
        St::BorderWidth => "5px 5px 0",
        St::BorderTopColor => color
    };

    let arrow_right_styles = style! {
        St::Top => percent(50),
        St::Left => 0,
        St::MarginTop => px(-5),
        St::BorderWidth => "5px 5px 5px 0",
        St::BorderRightColor => color
    };

    let arrow_bottom_styles = style! {
        St::Top => 0,
        St::Left => percent(50),
        St::MarginLeft => px(-5),
        St::BorderWidth => "0 5px 5px",
        St::BorderBottomColor => color
    };

    let arrow_left_styles = style! {
        St::Top => percent(50),
        St::Right => 0,
        St::MarginTop => px(-5),
        St::BorderWidth => "5px 0 5px 5px",
        St::BorderLeftColor => color
    };

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
        St::MarginLeft => px(3),
        St::PaddingLeft => px(5)
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
        St::Transform => "translate(-100%,50%)",
        St::MarginRight => px(3),
        St::PaddingRight => px(5)
    };

    let (arrow_style, tooltip_style) = match direction {
        TooltipPlacement::Left => (arrow_left_styles, tooltip_left_styles),
        TooltipPlacement::Right => (arrow_right_styles, tooltip_right_styles),
        TooltipPlacement::Top => (arrow_top_styles, tooltip_top_styles),
        TooltipPlacement::Bottom => {
            (arrow_bottom_styles, tooltip_bottom_styles)
        }
    };

    div![
        class![
            C.absolute,
            C.break_words,
            C.hidden,
            C.group_hover__block,
            C.pointer_events_none,
            C.z_10
        ],
        tooltip_style,
        div![
            class![C.w_0, C.h_0, C.border_solid, C.absolute, C.opacity_90,],
            arrow_style,
        ],
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
                St::MinWidth => px(100),
                St::MaxWidth => px(200),
                St::BackgroundColor => color,
            },
            content
        ]
    ]
}

/// Render a tooltip.
pub fn tooltip<T>(content: &str, direction: TooltipPlacement) -> Node<T> {
    color_tooltip(content, direction, "black")
}

/// Render a tooltip with a red error color.
pub fn error_tooltip<T>(content: &str, direction: TooltipPlacement) -> Node<T> {
    color_tooltip(content, direction, "red")
}
