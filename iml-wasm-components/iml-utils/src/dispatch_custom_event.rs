// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use seed::{prelude::*, window};

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
