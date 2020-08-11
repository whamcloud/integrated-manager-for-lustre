use crate::{GMsg, Orders};
use js_sys::Array;
use seed::browser::util::ClosureNew;
use wasm_bindgen::prelude::*;
use wasm_bindgen::{closure::Closure, JsCast};
use web_sys::{DomRectReadOnly, Element};

#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(extends=js_sys::Object, js_name=ResizeObserver, typescript_type="ResizeObserver")]
    #[derive(Debug, Clone, PartialEq, Eq)]
    #[doc = "The `ResizeObserver` class."]
    #[doc = ""]
    #[doc = "[MDN Documentation](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver)"]
    pub type ResizeObserver;
    #[wasm_bindgen(catch, constructor, js_class = "ResizeObserver")]
    #[doc = "The `new ResizeObserver(..)` constructor, creating a new instance of `ResizeObserver`."]
    #[doc = ""]
    #[doc = "[MDN Documentation](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver/ResizeObserver)"]
    pub fn new(resize_callback: &js_sys::Function) -> Result<ResizeObserver, JsValue>;
    #[wasm_bindgen(method, structural, js_class="ResizeObserver" , js_name=disconnect)]
    #[doc = "The `disconnect()` method."]
    #[doc = ""]
    #[doc = "[MDN Documentation](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver/disconnect)"]
    pub fn disconnect(this: &ResizeObserver);
    #[wasm_bindgen(method, structural, js_class="ResizeObserver", js_name=observe)]
    #[doc = "The `observe()` method."]
    #[doc = ""]
    #[doc = "[MDN Documentation](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver/observe)"]
    pub fn observe(this: &ResizeObserver, target: &Element);
    #[wasm_bindgen( method , structural , js_class = "ResizeObserver" , js_name = unobserve )]
    #[doc = "The `unobserve()` method."]
    #[doc = ""]
    #[doc = "[MDN Documentation](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserver/unobserve)"]
    #[doc = ""]
    pub fn unobserve(this: &ResizeObserver, target: &Element);
}

#[wasm_bindgen]
extern "C" {
    #[wasm_bindgen(extends=js_sys::Object, js_name=ResizeObserverEntry, typescript_type = "ResizeObserverEntry")]
    #[derive(Debug, Clone, PartialEq, Eq)]
    #[doc = "The `ResizeObserverEntry` class."]
    #[doc = ""]
    #[doc = "[MDN Documentation](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserverEntry)"]
    pub type ResizeObserverEntry;
    #[wasm_bindgen(structural, method, getter, js_class="ResizeObserverEntry", js_name=contentRect)]
    #[doc = "Getter for the `contentRect` field of this object."]
    #[doc = ""]
    #[doc = "[MDN Documentation](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserverEntry/contentRect)"]
    #[doc = ""]
    #[doc = "*This API requires the following crate features to be activated: `DomRectReadOnly`*"]
    pub fn content_rect(this: &ResizeObserverEntry) -> Option<DomRectReadOnly>;
    #[wasm_bindgen(structural, method, getter, js_class = "ResizeObserverEntry", js_name=target)]
    #[doc = "Getter for the `target` field of this object."]
    #[doc = ""]
    #[doc = "[MDN Documentation](https://developer.mozilla.org/en-US/docs/Web/API/ResizeObserverEntry/target)"]
    #[doc = ""]
    pub fn target(this: &ResizeObserverEntry) -> Element;
}

/// Wraps a `ResizeObserver` instance and it's closure.
///
/// The Closure must live as long as the Observer, so we keep it alive by adding it
/// as an "unused" field.
pub struct ResizeObserverWrapper {
    inner: ResizeObserver,
    #[allow(dead_code)]
    closure: Closure<dyn FnMut(Array)>,
}

impl ResizeObserverWrapper {
    pub fn disconnect(&self) {
        self.inner.disconnect()
    }
    pub fn observe(&self, target: &Element) {
        self.inner.observe(target);
    }
    pub fn unobserve(&self, target: &Element) {
        self.inner.unobserve(target);
    }
}

impl Drop for ResizeObserverWrapper {
    fn drop(&mut self) {
        self.disconnect()
    }
}

pub fn init<F, T>(orders: &mut impl Orders<T, GMsg>, msg: F) -> ResizeObserverWrapper
where
    T: 'static,
    F: Fn(Vec<ResizeObserverEntry>) -> T + 'static,
{
    let (app, msg_mapper) = (orders.clone_app(), orders.msg_mapper());

    let closure = Closure::new(move |entries: Array| {
        let xs = entries.iter().map(JsCast::unchecked_into).collect();

        app.update(msg_mapper(msg(xs)));
    });

    let inner = ResizeObserver::new(closure.as_ref().unchecked_ref()).unwrap();

    ResizeObserverWrapper { inner, closure }
}
