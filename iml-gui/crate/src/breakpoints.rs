//! # Breakpoints
//!
//! This module lists the existing media breakpoints we use and contains some helper functions for working with them.
//!
//! It should be kept in sync with any breakpoint changes to `tailwind.config.js`.

use seed::window;

pub(crate) const SM: f64 = 569.;
pub(crate) const MD: f64 = 769.;
pub(crate) const LG: f64 = 1025.;
pub(crate) const XL: f64 = 1701.;

#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd)]
pub(crate) enum Size {
    XS,
    SM,
    MD,
    LG,
    XL,
}

fn inner_width() -> f64 {
    window()
        .inner_width()
        .expect("Could not get inner_width")
        .as_f64()
        .expect("Could not parse inner_width to f64")
}

/// Returns *maximum* matching breakpoint based on `window.inner_width`.
/// This models the behavior of breakpoints in tailwind: https://tailwindcss.com/docs/responsive-design/
pub(crate) fn size() -> Size {
    let w = inner_width();

    if w >= XL {
        Size::XL
    } else if w >= LG {
        Size::LG
    } else if w >= MD {
        Size::MD
    } else if w >= SM {
        Size::SM
    } else {
        Size::XS
    }
}
