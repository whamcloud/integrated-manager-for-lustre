use crate::Msg;
use iml_wire_types::warp_drive::ArcCache;
use seed::{prelude::*, *};

#[derive(Default)]
pub struct Model {
    pub host_name: String,
}

pub fn view(_: &ArcCache, model: &Model) -> impl View<Msg> {
    iframe![attrs! {
        At::Src => format!("https://localhost:7444/grafana/d/elloIaQZz/server-dashboard?var-host_name={}&orgId=1&from=now-15m&to=now&kiosk", model.host_name),
        At::Width => "100%",
        At::Height => "100%",
        "frameborder" => 0
    }]
}
