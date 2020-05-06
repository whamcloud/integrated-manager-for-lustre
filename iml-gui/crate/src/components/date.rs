// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{attrs, tooltip, Placement},
    generated::css_classes::C,
};
use chrono::{offset::FixedOffset, DateTime};
use seed::{prelude::*, *};

#[derive(Default)]
pub struct Model {
    pub(crate) basedate: Option<DateTime<FixedOffset>>,
}

impl Model {
    fn timeago(&self, date: &DateTime<FixedOffset>) -> Option<String> {
        self.basedate
            .map(|sd| format!("{}", chrono_humanize::HumanTime::from(*date - sd)))
    }
}

pub(crate) fn view<T>(m: &Model, date: &DateTime<FixedOffset>) -> Node<T> {
    let ds = date.to_rfc2822();
    if let Some(d) = m.timeago(date) {
        span![
            class![C.underline, C.whitespace_no_wrap],
            style! {"text-decoration-style" => "dotted"},
            attrs::container(),
            d,
            tooltip::view(&ds, Placement::Top)
        ]
    } else {
        span![class![C.whitespace_no_wrap], ds]
    }
}
