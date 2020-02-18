use crate::Msg;
use seed::{prelude::*, *};

#[derive(Default)]
pub struct Model {}

pub fn view(_: &Model) -> impl View<Msg> {
    iframe![attrs! {
        At::Src => "https://localhost:7444/grafana/d/2vkrIIQWz/fs-dashboard?orgId=1&from=1581968869809&to=1581969769809&kiosk",
        At::Width => "100%",
        At::Height => "100%",
        "frameborder" => 0
    }]
}
