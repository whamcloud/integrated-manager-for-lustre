// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub mod dropdown;
pub mod lnet_status;
pub mod modal;
pub mod paging;
pub mod panel;
pub mod popover;
pub mod progress_circle;
pub mod resource_links;
pub mod table;
pub mod toast;
pub mod tooltip;

pub(crate) mod action_dropdown;
pub(crate) mod activity_indicator;
pub(crate) mod alert_indicator;
pub(crate) mod arrow;
pub(crate) mod attrs;
pub(crate) mod breadcrumbs;
pub(crate) mod chart;
pub(crate) mod command_modal;
pub(crate) mod dashboard;
pub(crate) mod date;
pub(crate) mod datepicker;
pub(crate) mod duration_picker;
pub(crate) mod font_awesome;
pub(crate) mod form;
pub(crate) mod grafana_chart;
pub(crate) mod loading;
pub(crate) mod lock_indicator;
pub(crate) mod logo;
pub(crate) mod restrict;
pub(crate) mod sfa_overview;
pub(crate) mod stratagem;
pub(crate) mod tree;

pub(crate) use activity_indicator::{update_activity_health, ActivityHealth};
pub(crate) use alert_indicator::alert_indicator;
pub(crate) use arrow::arrow;
pub(crate) use font_awesome::{font_awesome, font_awesome_outline};
pub use logo::{ai_200x, ai_400x, ai_7990x, ddn_logo, ddn_logo_lettering, exa5, whamcloud_logo};

#[derive(Debug, Clone, Copy)]
pub enum Placement {
    Left,
    Right,
    Top,
    Bottom,
}

impl From<&Placement> for &str {
    fn from(p: &Placement) -> Self {
        match p {
            Placement::Left => "left",
            Placement::Right => "right",
            Placement::Top => "top",
            Placement::Bottom => "bottom",
        }
    }
}
