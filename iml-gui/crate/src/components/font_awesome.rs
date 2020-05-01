// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::generated::css_classes::C;
use seed::{prelude::*, virtual_dom::Attrs, *};

pub fn font_awesome_outline<T>(more_attrs: Attrs, icon_name: &str) -> Node<T> {
    font_awesome_base("regular", more_attrs, icon_name)
}

pub fn font_awesome<T>(more_attrs: Attrs, icon_name: &str) -> Node<T> {
    font_awesome_base("solid", more_attrs, icon_name)
}

fn font_awesome_base<T>(sprite_sheet: &str, more_attrs: Attrs, icon_name: &str) -> Node<T> {
    let mut attrs = class![C.fill_current];
    attrs.merge(more_attrs);

    svg![
        attrs,
        r#use![
            class![C.pointer_events_none],
            attrs! {
                At::Href => format!("sprites/{}.svg#{}", sprite_sheet, icon_name),
            }
        ]
    ]
}
