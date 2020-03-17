use seed::prelude::*;
use iml_wire_types::db::DeviceRecord;
use std::sync::Arc;

#[derive(Clone)]
pub enum Msg {
    SetDevice(Arc<DeviceRecord>),
}

pub struct Model {
    pub id: u32,
}

pub fn view(_model: &Model) -> impl View<crate::Msg> {
    seed::empty()
}
