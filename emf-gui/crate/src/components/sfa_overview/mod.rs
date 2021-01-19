// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod enclosures;

use crate::{
    components::{attrs, tooltip, Placement},
    extensions::MergeAttrs,
    font_awesome::{font_awesome, font_awesome_outline},
    generated::css_classes::C,
    page::RecordChange,
    resize_observer, GMsg,
};
use emf_wire_types::{
    sfa::{HealthState, SfaController, SfaDiskDrive, SfaEnclosure, SfaPowerSupply, SfaStorageSystem},
    warp_drive::{ArcCache, ArcRecord, RecordId},
};
use enclosures::{expansions, ss200nv, ss9012};
use seed::{prelude::*, *};
use std::{borrow::Cow, collections::HashMap, sync::Arc};

pub trait ToHealthState {
    fn to_health_state(&self) -> HealthState;
    fn to_health_state_reason(&self) -> Cow<'_, str>;
}

impl ToHealthState for Option<&SfaPowerSupply> {
    fn to_health_state(&self) -> HealthState {
        self.as_ref().map(|x| x.health_state).unwrap_or_default()
    }
    fn to_health_state_reason(&self) -> Cow<'_, str> {
        self.as_ref()
            .map(|x| Cow::Borrowed(x.health_state_reason.as_str()))
            .map(|x| if x.is_empty() { Cow::Borrowed("Healthy") } else { x })
            .unwrap_or_else(|| Cow::Borrowed("Status Unknown"))
    }
}

impl ToHealthState for Option<&SfaController> {
    fn to_health_state(&self) -> HealthState {
        self.as_ref()
            .map(|x| std::cmp::max(x.health_state, x.child_health_state))
            .unwrap_or_default()
    }
    fn to_health_state_reason(&self) -> Cow<'_, str> {
        let x = match self.as_ref() {
            Some(x) => x,
            None => return Cow::Borrowed("Status Unknown"),
        };

        if [HealthState::NonCritical, HealthState::Critical].contains(&x.child_health_state)
            && x.child_health_state > x.health_state
        {
            Cow::Owned(format!(
                "A {} issue has been detected with at least one element within the controller.",
                sfa_status_text(&x.child_health_state)
            ))
        } else if x.health_state_reason.is_empty() {
            Cow::Borrowed("Healthy")
        } else {
            Cow::Borrowed(&x.health_state_reason)
        }
    }
}

impl ToHealthState for &SfaEnclosure {
    fn to_health_state(&self) -> HealthState {
        std::cmp::max(self.health_state, self.child_health_state)
    }
    fn to_health_state_reason(&self) -> Cow<'_, str> {
        if [HealthState::NonCritical, HealthState::Critical].contains(&self.child_health_state)
            && self.child_health_state > self.health_state
        {
            Cow::Owned(format!(
                "A {} issue has been detected with at least one element within the enclosure.",
                sfa_status_text(&self.child_health_state)
            ))
        } else if self.health_state_reason.is_empty() {
            Cow::Borrowed("Healthy")
        } else {
            Cow::Borrowed(&self.health_state_reason)
        }
    }
}

impl ToHealthState for &SfaStorageSystem {
    fn to_health_state(&self) -> HealthState {
        std::cmp::max(self.health_state, self.child_health_state)
    }
    fn to_health_state_reason(&self) -> Cow<'_, str> {
        if [HealthState::NonCritical, HealthState::Critical].contains(&self.child_health_state)
            && self.child_health_state > self.health_state
        {
            Cow::Owned(format!(
                "A {} issue has been detected with at least one element within the subsystem.",
                sfa_status_text(&self.child_health_state)
            ))
        } else if self.health_state_reason.is_empty() {
            Cow::Borrowed("Healthy")
        } else {
            Cow::Borrowed(&self.health_state_reason)
        }
    }
}

#[derive(Debug, PartialEq, Eq)]
enum HeadEnclosure {
    SS200NV(ss200nv::Model),
}

impl ToString for HeadEnclosure {
    fn to_string(&self) -> String {
        match self {
            Self::SS200NV(_) => "SS200NV".to_string(),
        }
    }
}

#[derive(Debug, PartialEq, Eq)]
pub(crate) enum Expansion {
    SS9012(ss9012::Model),
}

impl Expansion {
    pub fn position(&self) -> i16 {
        match self {
            Self::SS9012(x) => x.enclosure.position,
        }
    }
}

#[derive(Debug)]
struct StorageSystem {
    data: Arc<SfaStorageSystem>,
    head_enclosure: Option<HeadEnclosure>,
    expansions: Vec<Expansion>,
}

#[derive(Default)]
pub struct Model {
    cramped: bool,
    resize_observer: Option<resize_observer::ResizeObserverWrapper>,
    systems: HashMap<i32, StorageSystem>,
}

fn build_head_enclosure(cache: &ArcCache, storage_system_id: &str) -> Option<HeadEnclosure> {
    cache
        .sfa_enclosure
        .values()
        .filter(|x| x.storage_system == storage_system_id)
        .find_map(|x| match x.model.as_ref() {
            "SS200NV" => Some(HeadEnclosure::SS200NV(ss200nv::Model {
                enclosure: Arc::clone(&x),
                disks: add_disks(&cache.sfa_disk_drive, storage_system_id, x.index),
                top_controller: add_controller(&cache.sfa_controller, &cache.sfa_enclosure, storage_system_id, "TOP"),
                bottom_controller: add_controller(
                    &cache.sfa_controller,
                    &cache.sfa_enclosure,
                    storage_system_id,
                    "BOTTOM",
                ),
                psu1: add_psu(&cache.sfa_power_supply, storage_system_id, x.index, 1),
                psu2: add_psu(&cache.sfa_power_supply, storage_system_id, x.index, 2),
            })),
            _ => None,
        })
}

pub(crate) fn build_expansion(cache: &ArcCache, enclosure: Arc<SfaEnclosure>) -> Option<Expansion> {
    match enclosure.model.as_ref() {
        "SS9012" => Some(Expansion::SS9012(ss9012::Model {
            disks: add_disks(&cache.sfa_disk_drive, &enclosure.storage_system, enclosure.index),
            psu1: add_psu(&cache.sfa_power_supply, &enclosure.storage_system, enclosure.index, 1),
            psu2: add_psu(&cache.sfa_power_supply, &enclosure.storage_system, enclosure.index, 2),
            psu3: add_psu(&cache.sfa_power_supply, &enclosure.storage_system, enclosure.index, 3),
            psu4: add_psu(&cache.sfa_power_supply, &enclosure.storage_system, enclosure.index, 4),
            psu5: add_psu(&cache.sfa_power_supply, &enclosure.storage_system, enclosure.index, 5),
            psu6: add_psu(&cache.sfa_power_supply, &enclosure.storage_system, enclosure.index, 6),
            enclosure,
        })),
        _ => None,
    }
}

fn build_expansions(cache: &ArcCache, storage_system_id: &str) -> Vec<Expansion> {
    let mut xs: Vec<_> = cache
        .sfa_enclosure
        .values()
        .filter(|x| x.storage_system == storage_system_id)
        .filter_map(|x| build_expansion(cache, Arc::clone(&x)))
        .collect();

    xs.sort_unstable_by(|a, b| a.position().partial_cmp(&b.position()).unwrap());

    xs
}

/// Given a map of `SfaDiskDrive`, returns the a Map of drives for a given storage system and enclosure keyed on slot id.
fn add_disks(
    disks: &im::HashMap<i32, Arc<SfaDiskDrive>>,
    storage_system_id: &str,
    enclosure_index: i32,
) -> HashMap<i32, Arc<SfaDiskDrive>> {
    disks
        .values()
        .filter(|x| x.storage_system == storage_system_id)
        .filter(|x| x.enclosure_index == enclosure_index)
        .map(|x| (x.slot_number, Arc::clone(x)))
        .collect()
}

fn add_psu(
    psus: &im::HashMap<i32, Arc<SfaPowerSupply>>,
    storage_system_id: &str,
    enclosure_index: i32,
    position: i16,
) -> Option<Arc<SfaPowerSupply>> {
    psus.values()
        .filter(|x| x.storage_system == storage_system_id)
        .filter(|x| x.enclosure_index == enclosure_index)
        .find(|x| x.position == position)
        .map(Arc::clone)
}

fn add_controller(
    controllers: &im::HashMap<i32, Arc<SfaController>>,
    enclosures: &im::HashMap<i32, Arc<SfaEnclosure>>,
    storage_system_id: &str,
    canister_location: &str,
) -> Option<Arc<SfaController>> {
    let enclosure = enclosures
        .values()
        .filter(|x| x.storage_system == storage_system_id)
        .find(|x| x.canister_location == canister_location)?;

    controllers
        .values()
        .filter(|x| x.storage_system == storage_system_id)
        .find(|x| x.enclosure_index == enclosure.index)
        .map(Arc::clone)
}

fn build_systems(cache: &ArcCache, model: &mut Model) -> bool {
    let mut changed = false;

    cache
        .sfa_storage_system
        .iter()
        .fold(&mut model.systems, |systems, (k, v)| {
            systems
                .entry(*k)
                .and_modify(|x| {
                    if v != &x.data {
                        changed = true;

                        x.data = Arc::clone(v);
                    }

                    let head_enclosure = build_head_enclosure(cache, &v.uuid);

                    if x.head_enclosure != head_enclosure {
                        changed = true;

                        x.head_enclosure = head_enclosure;
                    }
                })
                .or_insert_with(|| {
                    changed = true;

                    StorageSystem {
                        data: Arc::clone(v),
                        head_enclosure: build_head_enclosure(cache, &v.uuid),
                        expansions: build_expansions(cache, &v.uuid),
                    }
                });

            systems
        });

    changed
}

#[derive(Clone, Debug)]
pub enum Msg {
    ResizeObserved(Vec<resize_observer::ResizeObserverEntry>),
    StartObserving,
}

impl RecordChange<Msg> for Model {
    fn update_record(&mut self, record: ArcRecord, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        match record {
            ArcRecord::SfaStorageSystem(_)
            | ArcRecord::SfaController(_)
            | ArcRecord::SfaDiskDrive(_)
            | ArcRecord::SfaPowerSupply(_)
            | ArcRecord::SfaEnclosure(_) => {
                let changed = build_systems(cache, self);

                if !changed {
                    orders.skip();
                }
            }
            _ => {}
        }
    }
    fn remove_record(&mut self, id: RecordId, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        match id {
            RecordId::SfaStorageSystem(_)
            | RecordId::SfaController(_)
            | RecordId::SfaDiskDrive(_)
            | RecordId::SfaPowerSupply(_)
            | RecordId::SfaEnclosure(_) => {
                let changed = build_systems(cache, self);

                if !changed {
                    orders.skip();
                }
            }
            _ => {}
        }
    }
    fn set_records(&mut self, cache: &ArcCache, orders: &mut impl Orders<Msg, GMsg>) {
        let changed = build_systems(cache, self);

        if !changed {
            orders.skip();
        }
    }
}

pub(crate) fn status_icon<T>(x: &HealthState) -> Node<T> {
    match x {
        HealthState::None => font_awesome(class![], "check"),
        HealthState::Ok => font_awesome(class![], "check"),
        HealthState::NonCritical => font_awesome_outline(class![], "bell"),
        HealthState::Critical => font_awesome_outline(class![], "bell"),
        HealthState::Unknown => font_awesome(class![], "check"),
    }
}

fn sfa_status_bg_color(x: &HealthState) -> &str {
    match x {
        HealthState::None => C.bg_gray_500,
        HealthState::Ok => C.bg_green_500,
        HealthState::NonCritical => C.bg_yellow_500,
        HealthState::Critical => C.bg_red_500,
        HealthState::Unknown => C.bg_gray_500,
    }
}

fn sfa_status_border_color(x: &HealthState) -> &str {
    match x {
        HealthState::None => C.border_gray_400,
        HealthState::Ok => C.border_green_400,
        HealthState::NonCritical => C.border_yellow_400,
        HealthState::Critical => C.border_red_400,
        HealthState::Unknown => C.border_gray_400,
    }
}

fn sfa_status_text_color(x: &HealthState) -> &str {
    match x {
        HealthState::None => C.text_gray_400,
        HealthState::Ok => C.text_green_400,
        HealthState::NonCritical => C.text_yellow_400,
        HealthState::Critical => C.text_red_400,
        HealthState::Unknown => C.text_gray_400,
    }
}

fn sfa_status_text(x: &HealthState) -> &str {
    match x {
        HealthState::None => "None",
        HealthState::Ok => "Ok",
        HealthState::NonCritical => "Non Critical",
        HealthState::Critical => "Critical",
        HealthState::Unknown => "Unknown",
    }
}

fn sfa_status<T>(x: &SfaStorageSystem, cramped: bool) -> Node<T> {
    let health = x.to_health_state();

    let txt = sfa_status_text(&health);

    div![
        class![
            sfa_status_bg_color(&health),
            C.text_white,
            C.text_center,
            C.px_3,
            C.py_1,
            C.rounded
        ],
        attrs::container(),
        tooltip::view(&x.to_health_state_reason(), Placement::Top),
        status_icon(&health).merge_attrs(class![C.fill_current, C.w_4, C.h_4, C.inline, C.mr_2]),
        if cramped { "" } else { "Status: " },
        txt
    ]
}

fn head_enclosure_view<T>(head_enclosure: &HeadEnclosure, cramped: bool) -> Node<T> {
    match head_enclosure {
        HeadEnclosure::SS200NV(x) => ss200nv::view(x, cramped),
    }
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::ResizeObserved(xs) => {
            if let Some(x) = xs.get(0).and_then(|x| x.content_rect()) {
                let last_cramp = model.cramped;

                if x.width() <= 600. {
                    model.cramped = true;
                } else {
                    model.cramped = false;
                }

                if last_cramp == model.cramped {
                    orders.skip();
                }
            }
        }
        Msg::StartObserving => {
            seed::document().get_element_by_id("sfa_overview").and_then(|el| {
                let observer = model.resize_observer.as_ref()?;

                observer.observe(&el);

                Some(())
            });
        }
    };
}

pub fn view<T>(model: &Model) -> Node<T> {
    // In the future we will support multiple subsystems.
    // For now we just take the first one we see.
    let system = model.systems.values().next();

    let title = system
        .as_ref()
        .map(|x| x.data.platform.as_str())
        .unwrap_or_else(|| "SFA");

    div![
        id!["sfa_overview"],
        class![C.bg_white, C.rounded_lg, C.flex, C.flex_col],
        div![
            class![C.px_6, C.bg_gray_200, C.grid, C.grid_cols_12],
            h3![class![C.py_4, C.font_normal, C.text_lg, C.col_span_4], title],
            if let Some(x) = system.as_ref() {
                div![
                    class![C.self_center, C.col_span_4, C.col_start_5 => !model.cramped, C.col_start_7 => model.cramped],
                    sfa_status(&x.data, model.cramped)
                ]
            } else {
                empty![]
            }
        ],
        div![
            class![C.h_full, C.min_h_80, C.p_2, C.flex],
            if let Some((x, y)) = system.as_ref().and_then(|x| x.head_enclosure.as_ref().map(|y| (y, x))) {
                div![
                    class![C.grid, C.gap_4, C.min_h_80, C.w_full],
                    head_enclosure_view(x, model.cramped),
                    expansions::view(&y.data.platform, &y.expansions),
                ]
            } else {
                text!["Head enclosure was not found"]
            }
        ]
    ]
}

pub fn init(model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    let resize_observer = resize_observer::init(orders, Msg::ResizeObserved);

    model.resize_observer = Some(resize_observer);

    orders.after_next_render(|_| Msg::StartObserving);
}
