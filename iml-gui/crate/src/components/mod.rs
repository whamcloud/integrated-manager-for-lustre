pub(crate) mod activity_indicator;
pub(crate) mod arrow;
pub(crate) mod font_awesome;
pub(crate) mod popover;
pub(crate) mod tooltip;

pub(crate) use activity_indicator::{
    activity_indicator, update_activity_health, ActivityHealth,
};
pub(crate) use arrow::arrow;
pub(crate) use font_awesome::font_awesome;
pub(crate) use popover::{popover, popover_content, popover_title};
pub(crate) use tooltip::{
    color_tooltip, error_tooltip, tooltip, tooltip_container,
};

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
