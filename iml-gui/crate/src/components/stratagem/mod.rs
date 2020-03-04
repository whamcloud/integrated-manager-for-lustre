use crate::GMsg;
use seed::prelude::*;

pub(crate) mod inode_table;

pub struct Model {
    pub inode_table: inode_table::Model,
}

#[derive(Clone)]
pub enum Msg {
    InodeTable(inode_table::Msg),
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
    inode_table::view(&model.inode_table).map_msg(Msg::InodeTable)
}
