use super::filesystem;
use crate::{
    components::{alert_indicator, lock_indicator, table as T, Placement},
    extensions::MergeAttrs,
    generated::css_classes::C,
    route::RouteId,
    Model, Msg, Route,
};
use iml_wire_types::warp_drive::ArcValuesExt;
use seed::{prelude::*, *};

pub fn view(model: &Model) -> impl View<Msg> {
    let fs = &model.records.filesystem;
    if fs.is_empty() {
        div![
            class![C.text_3xl, C.text_center],
            h1![class![C.m_2, C.text_gray_600], "No file systems are configured"],
        ]
    } else {
        div![
            class![C.bg_white, C.border_t, C.border_b, C.border, C.rounded_lg, C.shadow],
            div![
                class![C.flex, C.justify_between, C.px_6, C._mb_px, C.bg_gray_200],
                h3![class![C.py_4, C.font_normal, C.text_lg], "File systems"]
            ],
            T::wrapper_view(vec![
                T::thead_view(vec![
                    T::th_view(plain!("File System")),
                    T::th_view(plain!("Management Server")),
                    T::th_view(plain!("Metadata Target Count")),
                    T::th_view(plain!("Connected Clients")),
                    T::th_view(plain!("Space Used / Total")),
                ]),
                tbody![fs.arc_values().map(|f| tr![
                    T::td_view(vec![
                        fs_link(f),
                        span![class![C.mx_1], lock_indicator::view(&model.locks, f)],
                        alert_indicator(&model.records.active_alert, f, true, Placement::Top)
                    ]),
                    T::td_view(filesystem::mgs(&model.records.target, f)),
                    T::td_right(plain!(f.mdts.len().to_string())),
                    T::td_right(filesystem::clients_view(f)),
                    T::td_view(filesystem::size_view(f)),
                    td!["TBD"]
                ],)],
            ],)
            .merge_attrs(class![C.pb_2]),
        ]
    }
}

fn fs_link<I>(f: &iml_wire_types::Filesystem) -> Node<I> {
    a![
        class![C.text_blue_500, C.hover__underline, C.block, C.h_full],
        attrs! {At::Href => Route::Filesystem(RouteId::from(f.id)).to_href()},
        &f.label
    ]
}
