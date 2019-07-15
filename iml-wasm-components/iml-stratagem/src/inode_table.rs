use bootstrap_components::bs_table::table;
use seed::{prelude::*, td, tr};

#[derive(serde::Deserialize, serde::Serialize, Debug, PartialEq, Clone)]
pub struct INode {
  classify_attr_type: String,
  counter_name: String,
  distribution_weight: String,
  count: u32,
}

#[derive(Default)]
pub struct Model {
  inodes: Vec<INode>,
  destroyed: bool,
}

#[derive(Clone)]
pub enum Msg {
  Destroy,
}

fn get_inode_elements<T>(inodes: &Vec<INode>) -> Vec<El<T>> {
  inodes
    .into_iter()
    .map(move |x| tr![td![x.counter_name], td![x.count.to_string()]])
    .collect()
}

/// View
pub fn render<T>(model: &Model) -> El<T> {
  if model.destroyed {
    seed::empty()
  } else {
    let inodes = get_inode_elements(&model.inodes);
    table(inodes)
  }
}