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
    cmp,
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
    fn add_attrs(self, attrs: Attrs) -> Self;
}

impl<T> AddAttrs for Node<T> {
    fn add_attrs(self, attrs: Attrs) -> Self {
        if let Node::Element(mut el) = self {
            el.attrs.merge(attrs);
            Node::Element(el)
        } else {
            self
        }
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

pub fn format_bytes(bytes: f64, precision: Option<usize>) -> String {
    let units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"];

    let bytes = bytes.max(0.0);
    let pwr = (bytes.ln() / 1024_f64.ln()).floor() as i32;
    let pwr = cmp::min(pwr, (units.len() - 1) as i32);
    let pwr = cmp::max(pwr, 0);
    let bytes = bytes / 1024_f64.powi(pwr);

    let bytes = format!("{:.*}", precision.unwrap_or(1), bytes);

    format!("{} {}", bytes, units[pwr as usize])
}

pub fn format_number(num: f64, precision: Option<usize>) -> String {
    let units = ["", "k", "M", "B", "T"];

    let sign = if num < 0_f64 { "-" } else { "" };

    let num = num.abs();

    let pwr = (num.ln() / 1000_f64.ln()).floor() as i32;
    let pwr = cmp::min(pwr, (units.len() - 1) as i32);
    let pwr = cmp::max(pwr, 0);

    let num = num / 1000_f64.powi(pwr);
    let num = format!("{:.*}", precision.unwrap_or(1), num);

    format!("{}{}{}", sign, num, units[pwr as usize])
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

    #[test]
    fn test_format_bytes_success() {
        assert_eq!(format_bytes(320.0, Some(0)), "320 B");
        assert_eq!(format_bytes(200_000.0, Some(1)), "195.3 KiB");
        assert_eq!(format_bytes(3_124_352.0, Some(3)), "2.980 MiB");
        assert_eq!(format_bytes(432_303_020_202.0, Some(3)), "402.614 GiB");
        assert_eq!(format_bytes(5_323_330_102_372.0, Some(2)), "4.84 TiB");
        assert_eq!(format_bytes(1000.0, Some(0)), "1000 B");
        assert_eq!(format_bytes(1024.0, Some(3)), "1.000 KiB");
        assert_eq!(format_bytes(4326.0, Some(4)), "4.2246 KiB");
        assert_eq!(format_bytes(3_045_827_469.0, Some(3)), "2.837 GiB");
        assert_eq!(format_bytes(84_567_942_345_572_238.0, Some(2)), "75.11 PiB");
        assert_eq!(
            format_bytes(5_213_456_204_567_832_146_028.0, Some(3)),
            "4.416 ZiB"
        );
        assert_eq!(format_bytes(139_083_776.0, Some(1)), "132.6 MiB");
    }

    #[test]
    fn test_format_number_success() {
        assert_eq!(format_number(22.0, Some(10)), "22.0000000000");
        assert_eq!(format_number(22.3, Some(10)), "22.3000000000");
        assert_eq!(format_number(22.3, Some(2)), "22.30");
        assert_eq!(format_number(22.3, Some(1)), "22.3");
        assert_eq!(format_number(0.023, Some(5)), "0.02300");
        assert_eq!(format_number(0.023, Some(1)), "0.0");
        assert_eq!(format_number(8007.0, Some(5)), "8.00700k");
        assert_eq!(format_number(8007.0, Some(3)), "8.007k");
        assert_eq!(format_number(8007.0, Some(2)), "8.01k");
        assert_eq!(format_number(8_007_000.0, Some(5)), "8.00700M");
        assert_eq!(format_number(8_007_000_000.0, Some(1)), "8.0B");
        assert_eq!(format_number(8_007_000_000_000.0, Some(1)), "8.0T");
        assert_eq!(format_number(800_700.0, Some(5)), "800.70000k");
        assert_eq!(format_number(8200.0, Some(5)), "8.20000k");
        assert_eq!(format_number(8200.0, Some(3)), "8.200k");
        assert_eq!(format_number(8200.0, Some(1)), "8.2k");
        assert_eq!(format_number(8200.0, Some(0)), "8k");
    }
}
