use crate::{components::table, generated::css_classes::C, route::RouteId, GMsg, Route};
use iml_wire_types::{db::DeviceRecord, warp_drive::ArcCache};
use seed::{prelude::*, *};
use std::sync::Arc;

#[derive(Default)]
pub struct Model {
    pub device: Vec<Arc<DeviceRecord>>,
}

#[derive(Clone)]
pub enum Msg {
    SetDevices(Vec<Arc<DeviceRecord>>),
}

pub fn init(cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
    orders.send_msg(Msg::SetDevices(cache.device.values().cloned().collect()));
}

pub fn update(msg: Msg, _cache: &ArcCache, model: &mut Model, _orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::SetDevices(xs) => {
            let mut devices: Vec<_> = xs;

            devices.sort_by(|a, b| natord::compare(&a.device.id, &b.device.id));

            model.device = devices;
        }
    }
}

pub fn view(model: &Model) -> impl View<crate::Msg> {
    div![
        class![C.bg_white],
        div![
            class![C.px_6, C.bg_gray_200],
            h3![class![C.py_4, C.font_normal, C.text_lg], "devices"]
        ],
        if model.device.is_empty() {
            div![
                class![C.text_3xl, C.text_center],
                h1![class![C.m_2, C.text_gray_600], "No devices found"],
            ]
        } else {
            table::wrapper_view(vec![
                table::thead_view(vec![table::th_view(plain!["Id"]), th![]]),
                tbody![model.device.iter().map(|x| tr![table::td_center(vec![a![
                    class![C.text_blue_500, C.hover__underline],
                    attrs! {At::Href => Route::Device(RouteId::from(x.record_id)).to_href()},
                    &x.device.id
                ],]),])],
            ])
        }
    ]
}
