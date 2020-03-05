use crate::{
    components::{
        font_awesome, modal,
        stratagem::{duration_picker, ActionResponse, StratagemScan},
    },
    extensions::{MergeAttrs, NodeExt},
    generated::css_classes::C,
    key_codes, GMsg, RequestExt,
};
use seed::{prelude::*, *};

#[derive(Default)]
pub struct Model {
    pub modal: modal::Model,
    pub report_duration: duration_picker::Model,
    pub purge_duration: duration_picker::Model,
    pub fs_id: u32,
    pub scanning: bool,
}

impl Model {
    pub fn new(fs_id: u32) -> Self {
        Self {
            fs_id,
            ..Default::default()
        }
    }
}

#[derive(Clone)]
pub enum Msg {
    ReportDurationPicker(duration_picker::Msg),
    PurgeDurationPicker(duration_picker::Msg),
    SubmitScan,
    Scanning,
    Scanned(Box<fetch::ResponseDataResult<ActionResponse>>),
    Modal(modal::Msg),
    Noop,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::ReportDurationPicker(msg) => duration_picker::update(msg, &mut model.report_duration),
        Msg::PurgeDurationPicker(msg) => duration_picker::update(msg, &mut model.purge_duration),
        Msg::SubmitScan => {
            model.scanning = true;
            let data = StratagemScan {
                filesystem: model.fs_id,
                report_duration: model.report_duration.value_as_ms(),
                purge_duration: model.purge_duration.value_as_ms(),
            };

            let req = fetch::Request::api_call("run_stratagem")
                .with_auth()
                .method(fetch::Method::Post)
                .send_json(&data);

            orders
                .perform_cmd(req.fetch_json_data(|x| Msg::Scanned(Box::new(x))))
                .send_msg(Msg::Scanning);

            log!("fetch scan stratagem endpoint", model.fs_id);
        }
        Msg::Scanning => {
            // Launch command modal here
        }
        Msg::Scanned(msg) => {
            log!("Finished scanning. Received msg:", msg);
            model.scanning = false;
            model.report_duration.reset();
            model.purge_duration.reset();
            orders.proxy(Msg::Modal).send_msg(modal::Msg::Close);
        }
        Msg::Modal(msg) => {
            log!("Sending close message to modal");
            modal::update(msg, &mut model.modal, &mut orders.proxy(Msg::Modal));
        }
        Msg::Noop => {}
    };
}

pub(crate) fn view(model: &Model) -> Node<Msg> {
    let input_cls = class![
        C.appearance_none,
        C.focus__outline_none,
        C.focus__shadow_outline,
        C.px_3,
        C.py_2,
        C.rounded_sm,
        C.text_gray_800,
        C.bg_gray_200,
        C.col_span_5,
    ];

    modal::bg_view(
        model.modal.open,
        Msg::Modal,
        modal::content_view(
            Msg::Modal,
            div![vec![
                modal::title_view(
                    Msg::Modal,
                    span![
                        "Scan Filesystem Now",
                        font_awesome(class![C.w_4, C.h_4, C.inline, C.ml_2], "chart-bar")
                    ]
                ),
                label!["Generate report for files older than:"],
                duration_picker::view(
                    &model.report_duration,
                    input![
                        &input_cls,
                        attrs! {
                            At::AutoFocus => true,
                            At::Placeholder => "Optional",
                        },
                    ],
                )
                .merge_attrs(class![C.grid, C.grid_cols_6, C.mb_2])
                .map_msg(Msg::ReportDurationPicker),
                label!["Purge files older than:"],
                duration_picker::view(
                    &model.purge_duration,
                    input![
                        &input_cls,
                        attrs! {
                            At::Placeholder => "Optional",
                        },
                    ],
                )
                .merge_attrs(class![C.grid, C.grid_cols_6])
                .map_msg(Msg::PurgeDurationPicker),
                modal::footer_view(vec![scan_now_button(model.scanning), cancel_button()]).merge_attrs(class![C.pt_8]),
            ]],
        )
        .with_listener(keyboard_ev(Ev::KeyDown, move |ev| match ev.key_code() {
            key_codes::ESC => Msg::Modal(modal::Msg::Close),
            _ => Msg::Noop,
        }))
        .merge_attrs(class![C.text_black]),
    )
}

fn cancel_button() -> Node<Msg> {
    button![
        class![
            C.bg_transparent,
            C.hover__bg_gray_100,
            C.py_2,
            C.px_4,
            C.ml_2,
            C.rounded_full,
            C.text_blue_500,
            C.hover__text_blue_400
        ],
        simple_ev(Ev::Click, modal::Msg::Close),
        "Cancel",
    ]
    .map_msg(Msg::Modal)
}

fn scan_now_button(scanning: bool) -> Node<Msg> {
    let spinner = if scanning {
        font_awesome(class![C.w_4, C.h_4, C.inline, C.pulse, C.ml_2], "spinner")
    } else {
        empty![]
    };

    let mut btn = button![
        class![
            C.bg_blue_500,
            C.hover__bg_blue_400,
            C.py_2,
            C.px_4,
            C.rounded_full,
            C.text_white,
        ],
        simple_ev(Ev::Click, Msg::SubmitScan),
        "Scan Now",
        spinner,
    ];

    if scanning {
        btn = btn
            .merge_attrs(attrs! {At::Disabled => true})
            .merge_attrs(class![C.cursor_not_allowed, C.opacity_50]);
    }

    btn
}
