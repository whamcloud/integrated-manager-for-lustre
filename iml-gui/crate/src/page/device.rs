use iml_wire_types::db::DeviceRecord;
use seed::prelude::*;
use std::sync::Arc;

#[derive(Clone, Debug)]
pub enum Msg {
    SetDevice(Arc<DeviceRecord>),
}

pub struct Model {
    pub id: u32,
}

pub fn view(_model: &Model) -> impl View<Msg> {
    seed::empty()
}
