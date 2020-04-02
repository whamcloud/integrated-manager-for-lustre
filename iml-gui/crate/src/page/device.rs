use crate::GMsg;
use iml_wire_types::db::DeviceRecord;
use seed::prelude::*;
use std::sync::Arc;

#[derive(Clone, Debug)]
pub enum Msg {
    SetDevice(Arc<DeviceRecord>),
    UpdateDevice(Arc<DeviceRecord>),
}

pub struct Model {
    pub device: Arc<DeviceRecord>,
}

pub fn update(msg: Msg, model: &mut Model, _orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::SetDevice(device) => {
            model.device = device;
        }
        Msg::UpdateDevice(device) => {
            model.device = device;
        }
    }
}

pub fn view(_model: &Model) -> impl View<Msg> {
    seed::empty()
}
