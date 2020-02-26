use crate::{
    components::{chart::fs_usage, dashboard::dashboard_container},
    generated::css_classes::C,
};
use seed::{prelude::*, *};

pub fn view<T>(model: &fs_usage::Model) -> Node<T> {
    if let Some(metrics) = &model.metric_data {
        let dashboard_chart = div![
            class![
                C.flex,
                C.flex_grow,
                C.content_start,
                C.items_center,
                C.justify_center,
                C.h_64
            ],
            div![
                class![C.w_1of3, C.text_right, C.p_2],
                p![
                    class![(&model.usage_color).into()],
                    format!("{}", number_formatter::format_bytes(metrics.bytes_used, Some(1)))
                ],
                p![class![C.text_gray_500, C.text_xs], "(Used)"]
            ],
            div![class![C.w_1of3], fs_usage::view(&model)],
            div![
                class![C.w_1of3, C.p_2],
                p![format!(
                    "{}",
                    number_formatter::format_bytes(metrics.bytes_avail, Some(1))
                )],
                p![class![C.text_gray_500, C.text_xs], "(Available)"]
            ]
        ];

        dashboard_container::view("Filesystem Space Usage", dashboard_chart)
    } else {
        dashboard_container::view("Filesystem Space Usage", fs_usage::view(&model))
    }
}
