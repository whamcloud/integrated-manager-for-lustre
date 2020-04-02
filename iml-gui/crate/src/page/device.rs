use crate::{components::panel, generated::css_classes::C, GMsg};
use iml_wire_types::db::DeviceRecord;

use seed::{nodes, prelude::*, *};
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

pub fn view(model: &Model) -> impl View<Msg> {
    nodes![panel::view(
        h3![
            class![C.py_4, C.font_normal, C.text_lg],
            &format!("Device: {}", model.device.device.id.0),
        ],
        div![
            class![C.grid, C.grid_cols_2, C.gap_4],
            div![class![C.px_6, C.py_4], "Size"],
            div![class![C.px_6, C.py_4], &format!("{}", model.device.device.size.0)],
            div![class![C.px_6, C.py_4], "Type"],
            div![class![C.px_6, C.py_4], &format!("{}", model.device.device.device_type)],
        ],
    ),]
}
