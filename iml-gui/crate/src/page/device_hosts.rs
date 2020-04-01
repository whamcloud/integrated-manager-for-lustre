use crate::{components::table, generated::css_classes::C, GMsg};
use iml_wire_types::{
    db::DeviceHostRecord,
    warp_drive::{ArcCache, RecordId},
};
use seed::{prelude::*, *};
use std::borrow::Cow;
use std::{cmp::Ordering, sync::Arc};

#[derive(Default)]
pub struct Model {
    pub device_host: Vec<Arc<DeviceHostRecord>>,
}

#[derive(Clone, Debug)]
pub enum Msg {
    SetDeviceHosts(Vec<Arc<DeviceHostRecord>>),
    UpdateDeviceHost(Arc<DeviceHostRecord>),
    Remove(RecordId),
}

pub fn init(cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
    orders.send_msg(Msg::SetDeviceHosts(cache.device_host.values().cloned().collect()));
}

fn compose_comparisons(a: Ordering, b: Ordering) -> Ordering {
    match a {
        Ordering::Less => a,
        Ordering::Equal => b,
        Ordering::Greater => a,
    }
}

pub fn update(msg: Msg, model: &mut Model, _orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::SetDeviceHosts(mut devices) => {
            devices.sort_by(|a, b| {
                let a_paths = {
                    let s: Vec<_> = a
                        .device_host
                        .paths
                        .0
                        .iter()
                        .map(|z| z.to_str().unwrap_or("Non-UTF-8 path").to_string())
                        .collect();
                    s.join(",")
                };
                let b_paths = {
                    let s: Vec<_> = b
                        .device_host
                        .paths
                        .0
                        .iter()
                        .map(|z| z.to_str().unwrap_or("Non-UTF-8 path").to_string())
                        .collect();
                    s.join(",")
                };
                compose_comparisons(
                    natord::compare(&a_paths, &b_paths),
                    natord::compare(a.device_host.fqdn.as_ref(), b.device_host.fqdn.as_ref()),
                )
            });

            model.device_host = devices;
        }
        Msg::UpdateDeviceHost(d) => {
            let devices = &mut model.device_host;

            devices.push(d);

            devices.sort_by(|a, b| {
                let a_paths = {
                    let s: Vec<_> = a
                        .device_host
                        .paths
                        .0
                        .iter()
                        .map(|z| z.to_str().unwrap_or("Non-UTF-8 path").to_string())
                        .collect();
                    s.join(",")
                };
                let b_paths = {
                    let s: Vec<_> = b
                        .device_host
                        .paths
                        .0
                        .iter()
                        .map(|z| z.to_str().unwrap_or("Non-UTF-8 path").to_string())
                        .collect();
                    s.join(",")
                };

                compose_comparisons(
                    natord::compare(&a_paths, &b_paths),
                    natord::compare(a.device_host.fqdn.as_ref(), b.device_host.fqdn.as_ref()),
                )
            });
        }
        Msg::Remove(d) => {
            let devices = &mut model.device_host;

            let i = devices.iter().position(|x| RecordId::DeviceHost(x.id) == d);

            if let Some(i) = i {
                devices.remove(i);
            } else {
                seed::log!("Element to remove not found");
            }
        }
    }
}

pub fn view(model: &Model) -> impl View<Msg> {
    div![
        class![C.bg_white],
        div![
            class![C.px_6, C.bg_gray_200],
            h3![class![C.py_4, C.font_normal, C.text_lg], "devices"]
        ],
        if model.device_host.is_empty() {
            div![
                class![C.text_3xl, C.text_center],
                h1![class![C.m_2, C.text_gray_600], "No devices hosts found"],
            ]
        } else {
            table::wrapper_view(vec![
                table::thead_view(vec![
                    table::th_view(plain!["Device Id"]),
                    table::th_view(plain!["Host"]),
                    table::th_view(plain!["Mount Path"]),
                    table::th_view(plain!["Local"]),
                    table::th_view(plain!["Paths"]),
                ]),
                tbody![model.device_host.iter().map(|x| tr![
                    table::td_view(vec![plain![Cow::from(x.device_host.device_id.0.clone())],]),
                    table::td_view(vec![plain![Cow::from(x.device_host.fqdn.0.clone())],]),
                    table::td_view(vec![plain![Cow::from(
                        x.device_host
                            .mount_path
                            .0
                            .as_ref()
                            .map(|y| y.to_str().unwrap_or("Non-UTF-8 path").to_string())
                            .unwrap_or("Not mounted".into())
                    )],]),
                    table::td_view(vec![plain![Cow::from(if x.device_host.local {
                        "Y".to_string()
                    } else {
                        "N".to_string()
                    })],]),
                    table::td_view(vec![plain![Cow::from({
                        let s: Vec<_> = x
                            .device_host
                            .paths
                            .0
                            .iter()
                            .map(|z| z.to_str().unwrap_or("Non-UTF-8 path").to_string())
                            .collect();
                        s.join(",")
                    })],]),
                ])],
            ])
        }
    ]
}
