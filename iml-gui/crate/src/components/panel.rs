use crate::generated::css_classes::C;
use seed::{prelude::*, *};

pub fn view<T>(heading: impl View<T>, body: impl View<T>) -> Node<T> {
    div![
        class![C.bg_white],
        div![class![C.px_6, C.bg_gray_200], heading.els()],
        div![body.els()]
    ]
}
