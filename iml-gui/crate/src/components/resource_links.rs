use crate::{extract_id, generated::css_classes::C, route::RouteId, Route};
use iml_wire_types::{Filesystem, Target, TargetConfParam, VolumeOrResourceUri};
use seed::{prelude::*, *};

pub fn server_link<T>(uri: Option<&String>, txt: &str) -> Node<T> {
    if let Some(u) = uri {
        let srv_id = extract_id(u).unwrap();
        a![
            class![C.text_blue_500, C.hover__underline, C.block],
            attrs! {At::Href => Route::Server(RouteId::from(srv_id)).to_href()},
            txt
        ]
    } else {
        plain!("N/A")
    }
}

pub fn volume_link<T>(t: &Target<TargetConfParam>) -> Node<T> {
    let vol_id = match &t.volume {
        VolumeOrResourceUri::ResourceUri(url) => extract_id(url).unwrap().parse::<u32>().unwrap(),
        VolumeOrResourceUri::Volume(v) => v.id,
    };

    a![
        class![C.text_blue_500, C.hover__underline, C.break_all],
        attrs! {At::Href => Route::Volume(RouteId::from(vol_id)).to_href()},
        t.volume_name,
    ]
}

pub fn fs_link<T>(x: &Filesystem) -> Node<T> {
    a![
        class![C.text_blue_500, C.hover__underline, C.break_all],
        attrs! {At::Href => Route::Filesystem(RouteId::from(x.id)).to_href()},
        &x.name,
    ]
}
