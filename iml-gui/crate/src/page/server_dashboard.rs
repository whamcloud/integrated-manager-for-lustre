use crate::Msg;
use iml_wire_types::warp_drive::ArcCache;
use seed::{prelude::*, *};

#[derive(Default)]
pub struct Model {
    pub host_name: String,
}

pub fn view(_: &ArcCache, model: &Model) -> impl View<Msg> {
    iframe![attrs! {
        At::Src => format!("https://localhost:7444/grafana/d/2vkrIIQWz/fs-dashboard?host_name={}&orgId=1&from=1581968869809&to=1581969769809&kiosk", model.host_name),
        At::Width => "100%",
        At::Height => "100%",
        "frameborder" => 0
    }]
}
