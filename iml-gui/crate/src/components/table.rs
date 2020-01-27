use crate::generated::css_classes::C;
use seed::{prelude::*, Attrs, *};

pub fn wrapper_cls() -> Attrs {
    class![C.table_auto, C.w_full]
}

pub fn wrapper_view<T>(children: impl View<T>) -> Node<T> {
    table![
        wrapper_cls(),
        style! {
            St::BorderSpacing => px(10),
            St::BorderCollapse => "initial"
        },
        children.els()
    ]
}

pub fn thead_view<T>(children: impl View<T>) -> Node<T> {
    thead![style! { St::BorderSpacing => "0 10px"}, tr![children.els()]]
}

pub fn th_cls() -> Attrs {
    class![C.px_3, C.text_gray_800, C.font_normal]
}

pub fn th_view<T>(children: impl View<T>) -> Node<T> {
    th![th_cls(), children.els()]
}

pub fn th_sortable_cls() -> Attrs {
    class![C.border_b_2, C.border_blue_500]
}

pub fn td_cls() -> Attrs {
    class![C.px_3, C.bg_gray_100, C.rounded, C.p_4]
}

pub fn td_view<T>(children: impl View<T>) -> Node<T> {
    td![td_cls(), children.els()]
}
