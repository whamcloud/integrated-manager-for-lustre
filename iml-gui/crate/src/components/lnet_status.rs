use crate::{components::font_awesome, generated::css_classes::C};
use iml_wire_types::db::LnetConfigurationRecord;
use seed::{prelude::*, *};

fn network<T>(color: impl Into<Option<&'static str>>) -> Node<T> {
    if let Some(color) = color.into() {
        font_awesome(class![C.w_4, C.h_4, C.inline, C.mr_1, color], "network-wired")
    } else {
        empty![]
    }
}

pub fn view<T>(x: &LnetConfigurationRecord) -> Node<T> {
    match x.state.as_str() {
        "lnet_up" => span![network(C.text_green_500), "Up"],
        "lnet_down" => span![network(C.text_red_500), "Down"],
        "lnet_unloaded" => span![network(C.text_yellow_500), "Unloaded"],
        "configured" => span![network(C.text_blue_500), "Configured"],
        "unconfigured" => span![network(None), "Unconfigured"],
        "undeployed" => span![network(None), "Undeployed"],
        _ => span![network(C.text_yellow_500), "Unknown"],
    }
}
