// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_wire_types::LockChange;
use regex::Regex;
use seed::{
    dom_types::{Attrs, Node},
    window,
};
use std::{
    collections::{HashMap, HashSet},
    mem,
};
use wasm_bindgen::JsValue;

pub trait IntoSerdeOpt {
    fn into_serde_opt<T>(&self) -> serde_json::Result<Option<T>>
    where
        T: for<'a> serde::de::Deserialize<'a>;
}

impl IntoSerdeOpt for JsValue {
    fn into_serde_opt<T>(&self) -> serde_json::Result<Option<T>>
    where
        T: for<'a> serde::de::Deserialize<'a>,
    {
        if self.is_undefined() || self.is_null() {
            Ok(None)
        } else {
            self.into_serde().map(Some)
        }
    }
}

pub trait AddAttrs {
    fn add_attrs(&mut self, attrs: Attrs) -> &mut Self;
}

impl<T> AddAttrs for Node<T> {
    fn add_attrs(&mut self, attrs: Attrs) -> &mut Self {
        if let Node::Element(el) = self {
            el.attrs.merge(attrs);
        }
        self
    }
}

pub trait Children<T> {
    fn get_children(&self) -> Option<&Vec<Node<T>>>;
}

impl<T> Children<T> for Node<T> {
    fn get_children(&self) -> Option<&Vec<Node<T>>> {
        if let Node::Element(el) = self {
            Some(&el.children)
        } else {
            None
        }
    }
}

pub fn extract_api(s: &str) -> Option<&str> {
    let re = Regex::new(r"^/?api/[^/]+/(\d+)/?$").unwrap();

    let x = re.captures(s)?;

    x.get(1).map(|x| x.as_str())
}

/// Sends the custom event up to the window, carrying with it the data.
pub fn dispatch_custom_event<T>(r#type: &str, data: &T)
where
    T: serde::Serialize + ?Sized,
{
    let js_value = JsValue::from_serde(data).expect("Error serializing data");
    let ev = web_sys::CustomEvent::new(r#type).expect("Could not create custom event");
    ev.init_custom_event_with_can_bubble_and_cancelable_and_detail(r#type, true, true, &js_value);

    window()
        .dispatch_event(&ev)
        .expect("Could not dispatch custom event");
}

#[derive(Debug, Copy, Clone)]
pub enum WatchState {
    Watching,
    Open,
    Close,
}

impl Default for WatchState {
    fn default() -> Self {
        WatchState::Close
    }
}

impl WatchState {
    pub fn is_open(self) -> bool {
        match self {
            WatchState::Open => true,
            _ => false,
        }
    }
    pub fn is_watching(self) -> bool {
        match self {
            WatchState::Watching => true,
            _ => false,
        }
    }
    pub fn should_update(self) -> bool {
        self.is_watching() || self.is_open()
    }
    pub fn update(&mut self) {
        match self {
            WatchState::Close => {
                mem::replace(self, WatchState::Watching);
            }
            WatchState::Watching => {
                mem::replace(self, WatchState::Open);
            }
            WatchState::Open => {
                mem::replace(self, WatchState::Close);
            }
        }
    }
}

/// A map of locks in which the key is a composite id string in the form `composite_id:id`
pub type Locks = HashMap<String, HashSet<LockChange>>;

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_extract_api_success() {
        assert_eq!(extract_api("/api/host/10").unwrap(), "10");
        assert_eq!(extract_api("/api/host/10/").unwrap(), "10");
        assert_eq!(extract_api("api/host/10").unwrap(), "10");
    }

    #[test]
    fn test_extract_api_failure() {
        assert_eq!(extract_api("foo"), None);
    }
}
