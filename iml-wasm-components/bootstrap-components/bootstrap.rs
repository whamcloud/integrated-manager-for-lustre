// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::ops::Deref;

pub mod bs_input {
    pub const INPUT_GROUP_BTN: &str = "input-group-btn";
}

pub struct Placement(&'static str);

impl Deref for Placement {
    type Target = str;

    fn deref(&self) -> &'static Self::Target {
        self.0
    }
}

pub const LEFT: Placement = Placement("left");
pub const RIGHT: Placement = Placement("right");
pub const TOP: Placement = Placement("top");
pub const BOTTOM: Placement = Placement("bottom");

pub const DISABLED: &str = "disabled";

pub mod bs_button {
    use seed::{attrs, button, class, div, dom_types::Attrs, prelude::*};

    pub const BTN: &str = "btn";
    pub const BTN_GROUP: &str = "btn-group";

    pub const BTN_DEFAULT: &str = "btn-default";
    pub const BTN_PRIMARY: &str = "btn-primary";
    pub const BTN_SUCCESS: &str = "btn-success";
    pub const BTN_INFO: &str = "btn-info";
    pub const BTN_WARNING: &str = "btn-warning";
    pub const BTN_DANGER: &str = "btn-danger";
    pub const BTN_LINK: &str = "btn-link";

    pub const LARGE: &str = "btn-lg";
    pub const SMALL: &str = "btn-sm";
    pub const EXTRASMALL: &str = "btn-xs";

    pub fn btn_cfg(more_attrs: Attrs) -> Attrs {
        let mut attrs = class![BTN];

        attrs.merge(attrs! { At::Type => "button" });
        attrs.merge(more_attrs);

        attrs
    }

    pub fn btn<T>(more_attrs: Attrs, children: Vec<Node<T>>) -> Node<T> {
        button![btn_cfg(more_attrs), children]
    }

    pub fn btn_group<T>(more_attrs: Attrs, children: Vec<Node<T>>) -> Node<T> {
        let mut attrs = class!["btn-group"];
        attrs.merge(more_attrs);

        div![attrs, children]
    }
}

pub mod bs_dropdown {
    use super::bs_button;
    use seed::{class, div, dom_types::Attrs, i, li, prelude::*, style, ul};
    use std::borrow::Cow;

    pub const DROPDOWN_MENU_RIGHT: &str = "dropdown_menu_right";
    pub const DROPDOWN_TOGGLE: &str = "dropdown-toggle";

    pub fn header<T>(label: &str) -> Node<T> {
        li![
            class!["dropdown-header"],
            style! {"user-select" => "none"},
            label
        ]
    }

    pub fn btn<T>(btn_name: impl Into<Cow<'static, str>>) -> Node<T> {
        bs_button::btn(
            class![DROPDOWN_TOGGLE],
            vec![
                Node::new_text(btn_name),
                i![class!["fa", "fa-fw", "fa-caret-down", "icon-caret-down"]],
            ],
        )
    }

    pub fn wrapper<T>(attrs: Attrs, open: bool, children: Vec<Node<T>>) -> Node<T> {
        let mut open = if open { class!["open"] } else { Attrs::empty() };
        open.merge(attrs);

        div![open, children]
    }

    pub fn menu<T>(children: Vec<Node<T>>) -> Node<T> {
        ul![class!["dropdown-menu"], children]
    }
}

pub mod popover {

    use super::Placement;
    use seed::{class, div, h3, prelude::*};

    pub fn wrapper<T>(open: bool, placement: &Placement, children: Vec<Node<T>>) -> Node<T> {
        if !open {
            return seed::empty();
        }

        div![
            class!["fade", "popover", "in", placement],
            div![class!["arrow"]],
            children
        ]
    }

    pub fn title<T>(el: Node<T>) -> Node<T> {
        h3![class!["popover-title"], el]
    }

    pub fn content<T>(el: Node<T>) -> Node<T> {
        div![class!["popover-content"], el]
    }
}

pub mod bs_table {
    use seed::{class, div, dom_types::Attrs, prelude::*, table};

    pub const TABLE_STRIPED: &str = "table-striped";
    pub const TABLE_HOVER: &str = "table-hover";

    pub fn table<T>(more_attrs: Attrs, children: Vec<Node<T>>) -> Node<T> {
        let mut attrs = class!["table"];
        attrs.merge(more_attrs);

        table![attrs, children]
    }

    pub fn table_responsive<T>(el: Node<T>) -> Node<T> {
        div![class!["table-responsive"], el]
    }
}

pub mod bs_well {
    use seed::{class, div, prelude::*};

    pub fn well<T>(children: Vec<Node<T>>) -> Node<T> {
        div![class!["well"], children]
    }
}

pub mod bs_panel {
    use seed::{class, div, prelude::*};

    pub fn panel<T>(els: Vec<Node<T>>) -> Node<T> {
        div![class!["panel", "panel-default"], els]
    }

    pub fn panel_heading<T>(el: Node<T>) -> Node<T> {
        div![class!["panel-heading"], el]
    }

    pub fn panel_body<T>(el: Node<T>) -> Node<T> {
        div![class!["panel-body"], el]
    }

    pub fn panel_footer<T>(els: Vec<Node<T>>) -> Node<T> {
        div![class!["panel-footer"], els]
    }
}

pub mod bs_modal {
    use seed::{class, div, prelude::*, style};

    pub fn modal<T>(children: Vec<Node<T>>) -> Node<T> {
        div![
            style! { "display" => "block", "z-index" => "9999" },
            class!["modal", "fade", "in"],
            div![
                class!["modal-dialog"],
                div![class!["modal-content"], children]
            ]
        ]
    }

    pub fn header<T>(children: Vec<Node<T>>) -> Node<T> {
        div![class!["modal-header"], children]
    }

    pub fn body<T>(children: Vec<Node<T>>) -> Node<T> {
        div![class!["modal-body"], children]
    }

    pub fn footer<T>(children: Vec<Node<T>>) -> Node<T> {
        div![class!["modal-footer"], children]
    }

    pub fn backdrop<T>() -> Node<T> {
        div![
            style! { "z-index" => "9998" },
            class!["modal-backdrop", "fade", "in"]
        ]
    }
}
