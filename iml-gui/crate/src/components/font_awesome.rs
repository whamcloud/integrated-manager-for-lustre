use crate::generated::css_classes::C;
use seed::{dom_types::Attrs, prelude::*, *};

pub fn font_awesome<T>(more_attrs: Attrs, icon_name: &str) -> Node<T> {
    let mut attrs = class![C.fill_current, C._my_px];
    attrs.merge(more_attrs);

    svg![
        attrs,
        r#use![attrs! {
            At::Href => format!("sprites/solid.svg#{}", icon_name),
        }]
    ]
}
