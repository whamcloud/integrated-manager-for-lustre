use crate::Msg;
use iml_wire_types::warp_drive::ArcCache;
use seed::{prelude::*, *};
use std::fmt;

#[derive(Default)]
pub struct Model {
    pub target_name: String,
}

pub enum TargetUsage {
    Object,
    File,
}

impl fmt::Display for TargetUsage {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match *self {
            TargetUsage::Object => write!(f, "Object"),
            TargetUsage::File => write!(f, "File"),
        }
    }
}

impl From<&str> for TargetUsage {
    fn from(item: &str) -> Self {
        if item.contains("OST") {
            TargetUsage::Object
        } else {
            TargetUsage::File
        }
    }
}

pub fn view(_: &ArcCache, model: &Model) -> impl View<Msg> {
    let object_or_files_title: TargetUsage = (model.target_name.as_str()).into();
    iframe![attrs! {
        At::Src => format!("https://localhost:7444/grafana/d/Fl_8QJQZk/target-dashboard?var-target_name={}&var-object_or_files_title={}&orgId=1&from=now-15m&to=now&kiosk", &model.target_name, object_or_files_title),
        At::Width => "100%",
        At::Height => "100%",
        "frameborder" => 0
    }]
}
