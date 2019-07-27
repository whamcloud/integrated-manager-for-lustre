use crate::inode_error::InodeError;
use bootstrap_components::bs_table;
use futures::Future;
use iml_environment::influx_root;
use seed::{
    class, div,
    dom_types::Attrs,
    fetch::{FetchObject, RequestController},
    h4, i,
    prelude::*,
    style, tbody, td, th, thead, tr,
};

#[derive(serde::Deserialize, serde::Serialize, Debug, PartialEq, Clone)]
pub struct INodeCount {
    uid: String,
    count: u32,
}

#[derive(Default, Debug)]
pub struct Model {
    inodes: Vec<INodeCount>,
    destroyed: bool,
    cancel: Option<futures::sync::oneshot::Sender<()>>,
    request_controller: Option<RequestController>,
}

#[derive(Clone, Debug)]
pub enum Msg {
    FetchInodes,
    InodesFetched(FetchObject<InfluxResults>),
    OnFetchError(InodeError),
    Destroy,
    Noop,
}

#[derive(serde::Deserialize, Clone, Debug)]
pub struct InfluxSeries {
    #[serde(skip)]
    name: String,
    #[serde(skip)]
    columns: Vec<String>,
    values: Vec<(String, String, u32)>,
}

#[derive(serde::Deserialize, Clone, Debug)]
pub struct InfluxResult {
    #[serde(skip)]
    statement_id: u16,
    series: Option<Vec<InfluxSeries>>,
}

#[derive(serde::Deserialize, Clone, Debug)]
pub struct InfluxResults {
    results: Vec<InfluxResult>,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut Orders<Msg>) {
    if model.destroyed {
        return;
    }

    match msg {
        Msg::FetchInodes => {
            model.cancel = None;

            let (fut, request_controller) = fetch_inodes();
            model.request_controller = request_controller;
            orders.skip().perform_cmd(fut);
        }
        Msg::InodesFetched(fetch_object) => {
            model.request_controller = None;

            match fetch_object.response() {
                Ok(response) => {
                    let mut data: InfluxResults = response.data;
                    model.inodes = data
                        .results
                        .drain(..)
                        .take(1)
                        .filter_map(|result| result.series)
                        .flatten()
                        .take(1)
                        .map(|v| v.values)
                        .flatten()
                        .map(|(_, uid, count)| INodeCount { uid, count })
                        .collect();
                }
                Err(fail_reason) => {
                    orders.send_msg(Msg::OnFetchError(fail_reason.into()));
                }
            }

            let sleep = iml_sleep::Sleep::new(60000)
                .map(move |_| Msg::FetchInodes)
                .map_err(|_| unreachable!());

            let (p, c) = futures::sync::oneshot::channel::<()>();

            model.cancel = Some(p);

            let c = c.map(move |_| Msg::Noop).map_err(move |_| {
                log::info!("Inodes poll timeout dropped");

                Msg::Noop
            });

            // Fetch the inodes after 60 seconds unless the producer is dropped before
            // it has an opportunity to fetch.
            let fut = sleep
                .select2(c)
                .map(futures::future::Either::split)
                .map(|(x, _)| x)
                .map_err(futures::future::Either::split)
                .map_err(|(x, _)| x);
            orders.perform_cmd(fut);
        }
        Msg::OnFetchError(e) => {
            log::error!("Fetch Error: {}", e);
            orders.skip();
        }
        Msg::Noop => {
            orders.skip();
        }
        Msg::Destroy => {
            model.cancel = None;

            if let Some(c) = model.request_controller.take() {
                c.abort()
            }

            model.destroyed = true;
            model.inodes = vec![];
        }
    }
}

pub fn fetch_inodes() -> (
    impl Future<Item = Msg, Error = Msg>,
    Option<seed::fetch::RequestController>,
) {
    let mut request_controller = None;
    let url:String = format!("{}db=iml_stratagem_scans&q=SELECT%20counter_name,%20count%20FROM%20stratagem_scan%20WHERE%20group_name=%27user_distribution%27", influx_root());
    let fut = seed::fetch::Request::new(url)
        .controller(|controller| request_controller = Some(controller))
        .fetch_json(Msg::InodesFetched);

    (fut, request_controller)
}

fn get_inode_elements<T>(inodes: &Vec<INodeCount>) -> Vec<El<T>> {
    inodes
        .into_iter()
        .map(|x| tr![td![x.uid], td![x.count.to_string()]])
        .collect()
}

fn detail_panel<T>(children: Vec<El<T>>) -> El<T> {
    div!(children)
        .add_style("display".into(), "grid".into())
        .add_style("grid-template-columns".into(), "50% 50%".into())
        .add_style("grid-row-gap".into(), px(20))
}

/// View
pub fn view(model: &Model) -> El<Msg> {
    if model.destroyed {
        seed::empty()
    } else {
        let entries = get_inode_elements(&model.inodes);

        div![
            h4![class!["section-header"], "Top inode Users"],
            if !entries.is_empty() {
                bs_table::table(
                    Attrs::empty(),
                    vec![thead![tr![th!["Name"], th!["Count"]]], tbody![entries]],
                )
            } else {
                div![detail_panel(vec![i![
                    class!["fa fa-circle-notch fa-spin".into()],
                    style! {
                        "grid-column" => "2",
                        "grid-row" => "1",
                        "width" => "40px",
                        "height" => "40px",
                        "margin-left" => "-20px",
                        "font-size" => "40px"
                    }
                ]])]
            }
        ]
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use futures::sync::{oneshot, oneshot::Sender};
    use seed::fetch::{Request, ResponseWithDataResult, Status, StatusCategory};
    use std::sync::{Arc, Mutex};
    use wasm_bindgen_test::wasm_bindgen_test_configure;

    wasm_bindgen_test_configure!(run_in_browser);

    use wasm_bindgen_test::*;

    #[derive(Debug)]
    pub struct TestModel {
        model: Model,
        p: Arc<Mutex<Option<Sender<El<Msg>>>>>,
    }

    fn destroy_after_delay() -> impl Future<Item = Msg, Error = Msg> {
        iml_sleep::Sleep::new(1000)
            .map(move |_| Msg::Destroy)
            .map_err(|_| unreachable!())
    }

    pub fn test_view(TestModel { p, model }: &TestModel) -> El<Msg> {
        let el = view(&model);

        if let Some(_) = &model.cancel {
            p.lock().unwrap().take().map(|p| p.send(el.clone()));
        }

        el
    }

    pub fn test_update(msg: Msg, model: &mut TestModel, orders: &mut Orders<Msg>) {
        update(msg.clone(), &mut model.model, orders);
        orders.perform_cmd(destroy_after_delay());
    }

    #[wasm_bindgen_test(async)]
    pub fn test_inodes_with_data() -> impl Future<Item = (), Error = JsValue> {
        pub fn render() -> impl Future<Item = (), Error = JsValue> {
            let (p, c) = oneshot::channel::<El<Msg>>();
            let test_model = TestModel {
                p: Arc::new(Mutex::new(Some(p))),
                model: Model::default(),
            };

            let app = seed::App::build(test_model, test_update, test_view)
                .mount(seed::body())
                .finish()
                .run();

            let results = r#"{
            "results": [
              {
                "statement_id": 0,
                "series": [
                  {
                    "name": "stratagem_scan",
                    "columns": [
                      "time",
                      "counter_name",
                      "count"
                    ],
                    "values": [
                      [
                        "2019-07-12T06:16:51.700191592Z",
                        "uid_0",
                        26
                      ],
                      [
                        "2019-07-12T06:16:51.700191592Z",
                        "uid_1",
                        13
                      ]
                    ]
                  }
                ]
              }
            ]
          }"#;

            let raw = web_sys::Response::new_with_opt_str(Some(results)).unwrap();
            let data: InfluxResults = serde_json::from_str(results).unwrap();

            let fetch_object: FetchObject<InfluxResults> = FetchObject {
                request: Request::new("/influx?db=iml_stratagem_scans&q=SELECT counter_name, count FROM stratagem_scan WHERE group_name='user_distribution'".into()),
                result: Ok(ResponseWithDataResult {
                    raw,
                    status: Status {code: 200, text: "OK".into(), category: StatusCategory::Success},
                    data: Ok(data)
                })
            };

            app.update(Msg::InodesFetched(fetch_object));

            c.map(|el| {
                let tr1 = el.children[0].clone();
                let th1 = tr1.children[0].children[0].clone().text;
                let th2 = tr1.children[1].children[0].clone().text;
                let tr2 = el.children[1].clone();
                let td21 = tr2.children[0].children[0].clone().text;
                let td22 = tr2.children[1].children[0].clone().text;
                let tr3 = el.children[2].clone();
                let td31 = tr3.children[0].children[0].clone().text;
                let td32 = tr3.children[1].children[0].clone().text;

                assert_eq!(th1, Some("Uid".into()));
                assert_eq!(th2, Some("Count".into()));
                assert_eq!(td21, Some("uid_0".into()));
                assert_eq!(td22, Some("26".into()));
                assert_eq!(td31, Some("uid_1".into()));
                assert_eq!(td32, Some("13".into()));
            })
            .map_err(|_| unreachable!())
        }

        render()
    }

    #[wasm_bindgen_test(async)]
    pub fn test_inodes_with_empty_results() -> impl Future<Item = (), Error = JsValue> {
        pub fn render() -> impl Future<Item = (), Error = JsValue> {
            let (p, c) = oneshot::channel::<El<Msg>>();
            let test_model = TestModel {
                p: Arc::new(Mutex::new(Some(p))),
                model: Model::default(),
            };

            let app = seed::App::build(test_model, test_update, test_view)
                .mount(seed::body())
                .finish()
                .run();

            let results = r#"{
                "results": []
            }"#;

            let raw = web_sys::Response::new_with_opt_str(Some(results)).unwrap();
            let data: InfluxResults = serde_json::from_str(results).unwrap();

            let fetch_object: FetchObject<InfluxResults> = FetchObject {
                request: Request::new("/influx?db=iml_stratagem_scans&q=SELECT counter_name, count FROM stratagem_scan WHERE group_name='user_distribution'".into()),
                result: Ok(ResponseWithDataResult {
                    raw,
                    status: Status {code: 200, text: "OK".into(), category: StatusCategory::Success},
                    data: Ok(data)
                })
            };

            app.update(Msg::InodesFetched(fetch_object));

            c.map(|el| {
                assert_eq!(el.children.len(), 0);
            })
            .map_err(|_| unreachable!())
        }

        render()
    }
}
