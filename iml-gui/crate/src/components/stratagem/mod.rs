use crate::{components::grafana_chart, extensions::MergeAttrs, generated::css_classes::C, GMsg};
use iml_wire_types::Filesystem;
use seed::{prelude::*, *};
use std::collections::HashMap;

pub(crate) mod inode_table;

pub struct Model {
    inode_table: inode_table::Model,
    grafana_vars: HashMap<String, String>,
}

#[derive(Clone)]
pub enum Msg {
    InodeTable(inode_table::Msg),
}

impl Model {
    pub fn new(fs: &Filesystem) -> Self {
        let mut vars = HashMap::new();
        vars.insert("fs_name".into(), fs.name.clone());
        Self {
            inode_table: inode_table::Model::new(&fs.name),
            grafana_vars: vars,
        }
    }
}

pub fn init(orders: &mut impl Orders<Msg, GMsg>) {
    orders.proxy(Msg::InodeTable).send_msg(inode_table::Msg::FetchInodes);
}

pub(crate) fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::InodeTable(x) => inode_table::update(x, &mut model.inode_table, &mut orders.proxy(Msg::InodeTable)),
    }
}
pub(crate) fn view(model: &Model) -> Node<Msg> {
    let last_scan = format!(
        "Last Scanned: {}",
        model.inode_table.last_known_scan.as_ref().unwrap_or(&"N/A".to_string())
    );

    div![
        inode_table::view(&model.inode_table).map_msg(Msg::InodeTable),
        caption_wrapper(
            "inode Usage Distribution",
            Some(&last_scan),
            stratagem_chart(&grafana_chart::GrafanaChartData {
                org_id: 1,
                refresh: "1m",
                panel_id: 2,
                vars: &model.grafana_vars
            })
        ),
        caption_wrapper(
            "Space Usage Distribution",
            Some(&last_scan),
            stratagem_chart(&grafana_chart::GrafanaChartData {
                org_id: 1,
                refresh: "1m",
                panel_id: 3,
                vars: &model.grafana_vars
            })
        )
    ]
}

fn stratagem_chart<T>(data: &grafana_chart::GrafanaChartData) -> Node<T> {
    grafana_chart::view("OBdCS5IWz", "stratagem", data).merge_attrs(attrs! {At::Width => "100%",
    At::Height => 400})
}

//TODO: move to the table module and use it where the tables are used as well:
fn caption_wrapper<T>(caption: &str, comment: Option<&str>, children: impl View<T>) -> Node<T> {
    div![
        class![
            C.bg_white,
            C.border,
            C.border_b,
            C.border_t,
            C.mt_24,
            C.rounded_lg,
            C.shadow,
        ],
        div![
            class![C.flex, C.justify_between, C.px_6, C._mb_px, C.bg_gray_200],
            h3![class![C.py_4, C.font_normal, C.text_lg], caption],
            if let Some(c) = comment {
                p![class![C.py_4, C.text_gray_600], c]
            } else {
                empty![]
            }
        ],
        children.els()
    ]
}
