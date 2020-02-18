use crate::{
    components::{action_dropdown, alert_indicator, lock_indicator, panel, resource_links, Placement},
    extensions::MergeAttrs,
    generated::css_classes::C,
    GMsg,
};
use iml_wire_types::{
    warp_drive::{ArcCache, Locks},
    Session, Target, TargetConfParam, ToCompositeId,
};
use seed::{prelude::*, *};
use std::sync::Arc;

pub struct Model {
    pub target: Arc<Target<TargetConfParam>>,
    dropdown: action_dropdown::Model,
}

impl Model {
    pub fn new(target: Arc<Target<TargetConfParam>>) -> Self {
        Self {
            dropdown: action_dropdown::Model::new(vec![target.composite_id()]),
            target,
        }
    }
}

#[derive(Clone, Debug)]
pub enum Msg {
    ActionDropdown(action_dropdown::IdMsg),
    UpdateTarget(Arc<Target<TargetConfParam>>),
}

pub fn update(msg: Msg, cache: &ArcCache, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::ActionDropdown(x) => {
            let action_dropdown::IdMsg(y, msg) = x;

            action_dropdown::update(
                action_dropdown::IdMsg(y, msg),
                cache,
                &mut model.dropdown,
                &mut orders.proxy(Msg::ActionDropdown),
            );
        }
        Msg::UpdateTarget(x) => {
            if x.id == model.target.id {
                model.target = x;
            }
        }
    }
}

pub fn view(cache: &ArcCache, model: &Model, all_locks: &Locks, session: Option<&Session>) -> Node<Msg> {
    panel::view(
        h3![
            class![C.py_4, C.font_normal, C.text_lg],
            &format!("Target: {}", model.target.name),
            lock_indicator::view(all_locks, &model.target).merge_attrs(class![C.ml_2]),
            alert_indicator(&cache.active_alert, &model.target, true, Placement::Right).merge_attrs(class![C.ml_2]),
        ],
        div![
            class![C.grid, C.grid_cols_2, C.gap_4],
            div![class![C.p_6], "Started On"],
            div![
                class![C.p_6],
                resource_links::server_link(model.target.active_host.as_ref(), &model.target.active_host_name)
            ],
            div![class![C.p_6], "Primary Server"],
            div![
                class![C.p_6],
                resource_links::server_link(Some(&model.target.primary_server), &model.target.primary_server_name)
            ],
            div![class![C.p_6], "Failover Server"],
            div![
                class![C.p_6],
                resource_links::server_link(
                    model.target.failover_servers.first(),
                    &model.target.failover_server_name
                )
            ],
            div![class![C.p_6], "Volume"],
            div![class![C.p_6], resource_links::volume_link(&model.target)],
            action_dropdown::view(model.target.id, &model.dropdown, all_locks, session)
                .merge_attrs(class![C.p_6, C.grid, C.col_span_2])
                .map_msg(Msg::ActionDropdown)
        ],
    )
}
