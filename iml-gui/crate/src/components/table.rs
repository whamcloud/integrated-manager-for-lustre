use crate::generated::css_classes::C;
use seed::{prelude::*, Attrs, *};

pub fn wrapper_cls() -> Attrs {
    class![C.table_auto, C.w_full]
}

pub fn wrapper_view<T>(more_attrs: Attrs, children: impl View<T>) -> Node<T> {
    let mut cls = wrapper_cls();

    cls.merge(more_attrs);

    table![
        cls,
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

pub fn th_view<T>(more_attrs: Attrs, children: impl View<T>) -> Node<T> {
    let mut cls = th_cls();

    cls.merge(more_attrs);

    th![cls, children.els()]
}

pub fn th_sortable_cls() -> Attrs {
    class![C.border_b_2, C.border_blue_500]
}

pub fn th_sortable_view<T>(more_attrs: Attrs, children: impl View<T>) -> Node<T> {
    let mut cls = th_sortable_cls();

    cls.merge(more_attrs);

    th_view(cls, children.els())
}

pub fn td_cls() -> Attrs {
    class![C.px_3, C.bg_gray_100, C.rounded, C.p_4]
}

pub fn td_view<T>(more_attrs: Attrs, children: impl View<T>) -> Node<T> {
    let mut cls = td_cls();

    cls.merge(more_attrs);

    td![cls, children.els()]
}
