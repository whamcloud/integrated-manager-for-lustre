// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! # Breakpoints
//!
//! This module lists the existing media breakpoints we use and contains some helper functions for working with them.
//!
//! It should be kept in sync with any breakpoint changes to `tailwind.config.js`.

use seed::window;

#[derive(Clone, Copy, Debug, Eq, PartialEq, Ord, PartialOrd)]
pub(crate) enum Size {
    XS = 0,
    SM = 569,
    MD = 769,
    LG = 1025,
    XL = 1701,
}

fn inner_width() -> u64 {
    window()
        .inner_width()
        .expect("Could not get inner_width")
        .as_f64()
        .expect("Could not parse inner_width to f64") as u64
}

/// Returns *maximum* matching breakpoint based on `window.inner_width`.
/// This models the behavior of breakpoints in tailwind: https://tailwindcss.com/docs/responsive-design/
pub(crate) fn size() -> Size {
    let w = inner_width();

    if w >= Size::XL as u64 {
        Size::XL
    } else if w >= Size::LG as u64 {
        Size::LG
    } else if w >= Size::MD as u64 {
        Size::MD
    } else if w >= Size::SM as u64 {
        Size::SM
    } else {
        Size::XS
    }
}
