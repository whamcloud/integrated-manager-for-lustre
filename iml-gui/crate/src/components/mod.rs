pub(crate) mod activity_indicator;
pub(crate) mod alert_indicator;
pub(crate) mod arrow;
pub(crate) mod breadcrumbs;
pub(crate) mod dropdown;
pub(crate) mod font_awesome;
pub(crate) mod paging;
pub(crate) mod popover;
pub(crate) mod table;
pub(crate) mod tooltip;
pub(crate) mod tree;

pub(crate) use activity_indicator::{activity_indicator, update_activity_health, ActivityHealth};
pub(crate) use alert_indicator::alert_indicator;
pub(crate) use arrow::arrow;
pub(crate) use font_awesome::{font_awesome, font_awesome_outline};

#[derive(Debug, Clone, Copy)]
pub(crate) enum Placement {
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
