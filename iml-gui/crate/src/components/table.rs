use crate::generated::css_classes::C;
use seed::{prelude::*, *};

pub fn wrapper_view<T>(children: impl View<T>) -> Node<T> {
    table![
        class![C.table_auto, C.w_full, C.text_center],
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

fn th_base<T>(more_attrs: Attrs, children: impl View<T>) -> Node<T> {
    let mut cls = class![C.px_3, C.text_left, C.text_gray_800, C.font_normal, C.text_center];

    cls.merge(more_attrs);

    th![cls, children.els()]
}

pub fn th_view<T>(children: impl View<T>) -> Node<T> {
    th_base(Attrs::empty(), children.els())
}

pub fn th_sortable_view<T>(children: impl View<T>) -> Node<T> {
    th_base(class![C.border_b_2, C.border_blue_500], children.els())
}

pub fn td_view<T>(children: impl View<T>) -> Node<T> {
    td![
        class![C.px_3, C.bg_gray_100, C.rounded, C.text_center, C.p_4],
        children.els()
    ]
}
