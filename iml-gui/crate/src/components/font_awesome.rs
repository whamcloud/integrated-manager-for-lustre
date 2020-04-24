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

// cool symbols
pub fn font_awesome_minus_circle<T>(awesome_style: Attrs) -> Node<T> {
    svg![
        awesome_style,
        attrs! { "focusable" => "false", "xmlns" => "http://www.w3.org/2000/svg", "viewBox" => "0 0 512 512"},
        path![attrs! {
            "fill" => "currentColor",
            "d" => "M140 274c-6.6 0-12-5.4-12-12v-12c0-6.6 5.4-12 12-12h232c6.6 0 12 5.4 12 \
             12v12c0 6.6-5.4 12-12 12H140zm364-18c0 137-111 248-248 248S8 393 8 256 119 8 \
             256 8s248 111 248 248zm-32 0c0-119.9-97.3-216-216-216-119.9 0-216 97.3-216 \
             216 0 119.9 97.3 216 216 216 119.9 0 216-97.3 216-216z",
        }]
    ]
}

pub fn font_awesome_plus_circle<T>(awesome_style: Attrs) -> Node<T> {
    svg![
        awesome_style,
        attrs! { "focusable" => "false", "xmlns" => "http://www.w3.org/2000/svg", "viewBox" => "0 0 512 512"},
        path![attrs! {
            "fill" => "currentColor",
            "d" => "M384 250v12c0 6.6-5.4 12-12 12h-98v98c0 6.6-5.4 12-12 12h-12c-6.6 \
            0-12-5.4-12-12v-98h-98c-6.6 0-12-5.4-12-12v-12c0-6.6 5.4-12 12-12h98v-98c0-6.6 \
            5.4-12 12-12h12c6.6 0 12 5.4 12 12v98h98c6.6 0 12 5.4 12 12zm120 6c0 137-111 \
            248-248 248S8 393 8 256 119 8 256 8s248 111 248 248zm-32 \
            0c0-119.9-97.3-216-216-216-119.9 0-216 97.3-216 216 0 119.9 97.3 216 216 216 \
            119.9 0 216-97.3 216-216z",
        }]
    ]
}
