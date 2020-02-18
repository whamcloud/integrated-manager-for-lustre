use crate::{
    components::{font_awesome, modal, attrs},
    generated::css_classes::C,
    Model,
    Msg,
};
use iml_wire_types::{
    warp_drive::{ArcCache, ArcValuesExt},
    Host, Label,
};
use seed::{prelude::*, *};

pub fn view(_model: &Model) -> impl View<Msg> {
    let nodes =
        vec![
            modal::title_view(|x| x, span!["test title"]).map_msg(|_| Msg::WindowClick),
            modal::content_view(|x| x, span!["test content"]).map_msg(|_| Msg::WindowClick),
            modal::footer_view(span!["test footer"]),
        ].els();

    div![
        attrs::container(),
        class![C.cursor_pointer],
        attrs! {At::TabIndex => 0},
        font_awesome(class![C.inline, C.w_4, C.h_4], "unlock"),
        nodes,
    ]
}


