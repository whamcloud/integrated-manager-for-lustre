pub mod fs_detail_page;
pub mod fs_page;

use iml_environment::ui_root;
use iml_pie_chart::pie_chart;
use iml_utils::extract_api;
use iml_utils::{format_bytes, format_number};
use iml_wire_types::{Target, TargetConfParam};
use seed::{a, attrs, div, prelude::*};

fn link<T>(href: &str, content: &str) -> Node<T> {
    a![attrs! { At::Href => href, At::Type => "button" }, content]
}

fn client_count(client_count: Option<f64>) -> String {
    match client_count {
        Some(x) => x.round().to_string(),
        None => "---".into(),
    }
}

fn ui_link<T>(path: &str, label: &str) -> Node<T> {
    link(&format!("{}{}", ui_root(), path), label)
}

fn server_link<T>(resource_uri: &str, name: &str) -> Node<T> {
    match extract_api(&resource_uri) {
        Some(x) => ui_link(&format!("configure/server/{}", x), name),
        None => Node::new_text("---"),
    }
}

fn mgt_link<T>(mgt: Option<&Target<TargetConfParam>>) -> Node<T> {
    match mgt {
        Some(mgt) => server_link(&mgt.primary_server, &mgt.primary_server_name),
        None => Node::new_text("---"),
    }
}

fn usage<T>(
    used: Option<f64>,
    total: Option<f64>,
    formatter: fn(f64, Option<usize>) -> String,
) -> Node<T> {
    div![match (used, total) {
        (Some(used), Some(total)) => {
            let mut pc = pie_chart(used, total, "#aec7e8", "#1f77b4");
            pc.add_style("width", px(18))
                .add_style("height", px(18))
                .add_style("vertical-align", "bottom")
                .add_style("margin-right", px(3));
            div![
                pc,
                formatter(used, Some(1)),
                " / ",
                formatter(total, Some(1)),
            ]
        }
        _ => Node::new_text("Calculating..."),
    }]
}

pub fn space_usage<T>(used: Option<f64>, total: Option<f64>) -> Node<T> {
    usage(used, total, format_bytes)
}

pub fn file_usage<T>(used: Option<f64>, total: Option<f64>) -> Node<T> {
    usage(used, total, format_number)
}
