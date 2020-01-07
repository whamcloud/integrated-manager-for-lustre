use crate::{generated::css_classes::C, Model, Msg};
use seed::{prelude::*, *};

pub fn view(model: &Model) -> impl View<Msg> {
    span![
        pre![
            class![C.whitespace_pre_wrap, C.text_base],
            format!("{:#?}", model.locks),
        ],
        pre![
            class![C.whitespace_pre_wrap, C.text_base],
            format!("{:#?}", model.records)
        ]
    ]
}
