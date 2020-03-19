use iml_wire_types::db::DeviceHostRecord;
use seed::prelude::*;
use std::sync::Arc;

#[derive(Clone)]
pub enum Msg {
    SetDevice(Arc<DeviceHostRecord>),
}

pub struct Model {
    pub id: u32,
}

pub fn view(_model: &Model) -> impl View<crate::Msg> {
    seed::empty()
}
