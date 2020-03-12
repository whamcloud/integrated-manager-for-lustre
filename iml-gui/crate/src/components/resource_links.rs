use crate::{extensions::MergeAttrs as _, extract_id, generated::css_classes::C, route::RouteId, Route};
use iml_wire_types::{Filesystem, Target, TargetConfParam, VolumeOrResourceUri};
use seed::{prelude::*, *};

pub fn href_view<T>(x: &str, route: Route) -> Node<T> {
    a![
        class![C.text_blue_500, C.hover__underline],
        attrs! {At::Href => route.to_href()},
        x
    ]
}

pub fn server_link<T>(uri: Option<&String>, txt: &str) -> Node<T> {
    if let Some(u) = uri {
        let srv_id = extract_id(u).unwrap();

        href_view(txt, Route::Server(RouteId::from(srv_id))).merge_attrs(class![C.block])
    } else {
        plain!["N/A"]
    }
}

pub fn volume_link<T>(t: &Target<TargetConfParam>) -> Node<T> {
    let vol_id = match &t.volume {
        VolumeOrResourceUri::ResourceUri(url) => extract_id(url).unwrap().parse::<u32>().unwrap(),
        VolumeOrResourceUri::Volume(v) => v.id,
    };

    href_view(&t.volume_name, Route::Volume(RouteId::from(vol_id))).merge_attrs(class![C.break_all])
}

pub fn fs_link<T>(x: &Filesystem) -> Node<T> {
    href_view(&x.name, Route::Filesystem(RouteId::from(x.id))).merge_attrs(class![C.break_all])
}
