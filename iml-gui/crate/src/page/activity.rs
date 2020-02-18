use crate::{
    components::{action_dropdown, font_awesome, loading},
    generated::css_classes::C,
    GMsg, MergeAttrs as _, RequestExt as _,
};
use iml_wire_types::{
    warp_drive::{ArcCache, Locks},
    Alert, AlertRecordType, AlertSeverity, ApiList, EndpointName as _, Session,
};
use seed::{prelude::*, *};
use std::collections::HashMap;

enum State {
    Loading,
    Loaded(ApiList<Alert>, HashMap<u32, Row>),
}

struct Row {
    dropdown: action_dropdown::Model,
}

pub struct Model {
    state: State,
}

impl Default for Model {
    fn default() -> Self {
        Self { state: State::Loading }
    }
}

#[derive(Clone)]
pub enum Msg {
    ActionDropdown(Box<action_dropdown::IdMsg>),
    ActionsFetched(Box<fetch::ResponseDataResult<ApiList<Alert>>>),
    FetchActions,
    WindowClick,
}

pub fn update(msg: Msg, cache: &ArcCache, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::FetchActions => {
            orders.skip().perform_cmd(
                fetch::Request::api_call(Alert::endpoint_name()).fetch_json_data(|x| Msg::ActionsFetched(Box::new(x))),
            );
        }
        Msg::ActionsFetched(r) => match *r {
            Ok(mut resp) => {
                log!(resp);

                let rows = add_rows(&mut resp);

                model.state = State::Loaded(resp, rows);
            }
            Err(fail_reason) => {
                error!("An error has occurred {:?}", fail_reason);
                orders.skip();
            }
        },
        Msg::ActionDropdown(msg) => {
            let action_dropdown::IdMsg(id, msg) = *msg;

            if let State::Loaded(_, rows) = &mut model.state {
                if let Some(x) = rows.get_mut(&id) {
                    action_dropdown::update(
                        action_dropdown::IdMsg(id, msg),
                        cache,
                        &mut x.dropdown,
                        &mut orders.proxy(|x| Msg::ActionDropdown(Box::new(x))),
                    );
                }
            }
        }
        Msg::WindowClick => {
            if let State::Loaded(_, rows) = &mut model.state {
                for (_, r) in rows.iter_mut() {
                    if r.dropdown.watching.should_update() {
                        r.dropdown.watching.update();
                    }
                }
            }
        }
    }
}

pub(crate) fn init(orders: &mut impl Orders<Msg, GMsg>) {
    orders.send_msg(Msg::FetchActions);
}

fn add_rows(alerts: &mut ApiList<Alert>) -> HashMap<u32, Row> {
    let mut hm = HashMap::new();

    alerts
        .objects
        .iter_mut()
        .filter(|x| x.active.unwrap_or_default() && !is_cmd(x.record_type))
        .for_each(|x| {
            hm.insert(
                x.id,
                Row {
                    dropdown: action_dropdown::Model::new(x.affected_composite_ids.take().unwrap_or_default()),
                },
            );
        });

    hm
}

pub(crate) fn view(model: &Model, session: Option<&Session>, all_locks: &Locks) -> impl View<Msg> {
    div![match &model.state {
        State::Loading => loading::view(),
        State::Loaded(alerts, rows) => div![
            class![C.bg_gray_300, C.border, C.rounded],
            div![
                class![C.px_6, C.py_4, C.bg_gray_200],
                div![class![C.font_medium, C.text_lg], "Activities"],
                div![
                    class![C.grid, C.grid_cols_2, C.items_center],
                    div![
                        class![C.col_span_1],
                        format!(
                            "Showing {} - {} of {} total",
                            alerts.meta.offset + 1,
                            alerts.meta.offset + alerts.meta.limit,
                            alerts.meta.total_count
                        )
                    ],
                    div![
                        class![C.grid, C.justify_end],
                        font_awesome(class![C.inline, C.w_4, C.h_4, C.text_blue_400], "filter")
                    ]
                ],
            ],
            alerts.objects.iter().map(|x| {
                let row = rows.get(&x.id);

                alert_item_view(all_locks, session, x, row)
            })
        ],
    }]
}

fn alert_icon_view(alert: &Alert) -> Node<Msg> {
    let cls = class![C.inline, C.w_4, C.h_4];

    match alert.record_type {
        AlertRecordType::AlertEvent
        | AlertRecordType::LearnEvent
        | AlertRecordType::SyslogEvent
        | AlertRecordType::StorageResourceLearnEvent => font_awesome(cls, "info-circle"),
        x if is_cmd(x) => font_awesome(cls, "terminal"),
        _ => font_awesome(cls, "bell"),
    }
}

fn is_cmd(x: AlertRecordType) -> bool {
    match x {
        AlertRecordType::CommandRunningAlert
        | AlertRecordType::CommandSuccessfulAlert
        | AlertRecordType::CommandErroredAlert
        | AlertRecordType::CommandCancelledAlert => true,
        _ => false,
    }
}

fn alert_item_color(alert: &Alert) -> &str {
    match (alert.record_type, alert.severity) {
        (AlertRecordType::CommandRunningAlert, _) => "gray",
        (AlertRecordType::CommandSuccessfulAlert, _) => "green",
        (AlertRecordType::CommandErroredAlert, _) => "red",
        (AlertRecordType::CommandCancelledAlert, _) => "gray",
        (_, AlertSeverity::DEBUG) => "gray",
        (_, AlertSeverity::INFO) => "blue",
        (_, AlertSeverity::WARNING) => "yellow",
        (_, AlertSeverity::ERROR) => "red",
        (_, AlertSeverity::CRITICAL) => "orange",
    }
}

fn alert_item_view(all_locks: &Locks, session: Option<&Session>, alert: &Alert, row: Option<&Row>) -> Node<Msg> {
    let color = alert_item_color(alert);
    let border_color = format!("border-{}-500", color);
    let icon_color = format!("text-{}-500", color);
    let bg_color = format!("bg-{}-400", color);

    let is_active = alert.active.unwrap_or_default();

    div![
        class![
            border_color.as_str(),
            bg_color.as_str() => is_active,
            C.bg_white => !is_active,
            C.border_l_8,
            C.gap_4,
            C.grid_cols_3,
            C.grid_flow_row,
            C.grid,
            C.items_center,
            C.mx_4,
            C.my_6
            C.p_4,
            C.rounded,
            C.text_white => is_active,
        ],
        div![class![C.row_span_1, C.col_span_2], alert.message],
        div![
            class![C.row_span_1, C.col_span_1, C.grid, C.justify_end],
            alert_icon_view(alert).merge_attrs(class![icon_color.as_str()])
        ],
        div![
            class![C.row_span_1, C.col_span_2],
            format!("Started {}", timeago(&alert.begin).unwrap_or_default())
        ],
        div![
            class![C.row_span_1, C.col_span_1, C.grid, C.justify_end],
            if let Some(row) = row {
                action_dropdown::unstyled_view(
                    alert.id,
                    &row.dropdown,
                    all_locks,
                    session,
                    class![C.bg_transparent, C.border, C.border_white],
                )
                .map_msg(|x| Msg::ActionDropdown(Box::new(x)))
            } else {
                empty![]
            }
        ],
        if let Some(end) = alert.end.as_ref() {
            div![
                class![C.row_span_1, C.col_span_2],
                format!("Ended {}", timeago(end).unwrap_or_default())
            ]
        } else {
            empty![]
        }
    ]
}

fn timeago(x: &str) -> Option<String> {
    let dt = chrono::DateTime::parse_from_rfc3339(x).unwrap();

    Some(format!("{}", chrono_humanize::HumanTime::from(dt)))
}
