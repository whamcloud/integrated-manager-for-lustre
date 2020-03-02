use crate::{GMsg, Msg, Orders};
use js_sys::Function;
use seed::browser::util::ClosureNew;
use std::env;
use wasm_bindgen::{closure::Closure, JsCast};
use web_sys::EventSource;

pub fn init(orders: &mut impl Orders<Msg, GMsg>) {
    let iml_port = env::var("IML_PORT").unwrap_or("8443".into());

    let localhost_uri = format!("https://localhost:{}/messaging", iml_port);
    let uri = if *crate::IS_PRODUCTION {
        "/messaging"
    } else {
        &localhost_uri
    };

    // FIXME: This should be proxied via webpack dev-server but there is an issue with buffering contents of SSE.
    let es = EventSource::new(uri).unwrap();

    register_eventsource_handle(EventSource::set_onopen, Msg::EventSourceConnect, &es, orders);

    register_eventsource_handle(EventSource::set_onmessage, Msg::EventSourceMessage, &es, orders);

    register_eventsource_handle(EventSource::set_onerror, Msg::EventSourceError, &es, orders);
}

pub fn register_eventsource_handle<T, F>(
    es_cb_setter: fn(&EventSource, Option<&Function>),
    msg: F,
    ws: &EventSource,
    orders: &mut impl Orders<Msg, GMsg>,
) where
    T: wasm_bindgen::convert::FromWasmAbi + 'static,
    F: Fn(T) -> Msg + 'static,
{
    let (app, msg_mapper) = (orders.clone_app(), orders.msg_mapper());

    let closure = Closure::new(move |data| {
        app.update(msg_mapper(msg(data)));
    });

    es_cb_setter(ws, Some(closure.as_ref().unchecked_ref()));
    closure.forget();
}
