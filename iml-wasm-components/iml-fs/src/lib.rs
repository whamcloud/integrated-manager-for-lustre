pub mod fs_detail_page;
pub mod fs_page;

use iml_environment::ui_root;
use iml_pie_chart::pie_chart;
use iml_utils::extract_api;
use iml_utils::{format_bytes, format_number};
use iml_wire_types::{Target, TargetConfParam};
use seed::{a, attrs, div, prelude::*};

fn link<T>(href: &str, content: &str) -> El<T> {
    a![attrs! { At::Href => href, At::Type => "button" }, content]
}

fn client_count(client_count: Option<f64>) -> String {
    match client_count {
        Some(x) => x.round().to_string(),
        None => "---".into(),
    }
}

fn ui_link<T>(path: &str, label: &str) -> El<T> {
    link(&format!("{}{}", ui_root(), path), label)
}

fn server_link<T>(resource_uri: &str, name: &str) -> El<T> {
    match extract_api(&resource_uri) {
        Some(x) => ui_link(&format!("configure/server/{}", x), name),
        None => El::new_text("---"),
    }
}

fn mgt_link<T>(mgt: Option<&Target<TargetConfParam>>) -> El<T> {
    match mgt {
        Some(mgt) => server_link(&mgt.primary_server, &mgt.primary_server_name),
        None => El::new_text("---"),
    }
}

fn usage<T>(
    used: Option<f64>,
    total: Option<f64>,
    formatter: fn(f64, Option<usize>) -> String,
) -> El<T> {
    div![match (used, total) {
        (Some(used), Some(total)) => div![
            pie_chart(used, total, "#aec7e8", "#1f77b4")
                .add_style("width".into(), px(18))
                .add_style("height".into(), px(18))
                .add_style("vertical-align".into(), "bottom".into())
                .add_style("margin-right".into(), px(3)),
            formatter(used, Some(1)),
            " / ",
            formatter(total, Some(1)),
        ],
        _ => El::new_text("Calculating..."),
    }]
}

pub fn space_usage<T>(used: Option<f64>, total: Option<f64>) -> El<T> {
    usage(used, total, format_bytes)
}

pub fn file_usage<T>(used: Option<f64>, total: Option<f64>) -> El<T> {
    usage(used, total, format_number)
}
