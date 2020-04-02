// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{font_awesome, modal},
    extensions::{MergeAttrs as _, NodeExt as _, RequestExt as _},
    generated::css_classes::C,
    key_codes, sleep_with_handle, GMsg,
};
use futures::channel::oneshot;
use iml_wire_types::{ApiList, Command, EndpointName, Job, Step};
use regex::{Captures, Regex};
use seed::{prelude::*, *};
use serde::de::DeserializeOwned;
use std::collections::{HashMap, HashSet};
use std::{sync::Arc, time::Duration};
use std::fmt;

/// The component polls `/api/command/` endpoint and this constant defines how often it does.
const POLL_INTERVAL: Duration = Duration::from_millis(1000);

type Job0 = Job<Option<()>>;

#[derive(Debug, Hash, PartialEq, Eq)]
pub enum Idx {
    Command(u32),
    Job(u32),
    Step(u32),
}

#[derive(Clone, Debug)]
pub enum Opens {
    None,
    Command(u32),
    CommandJob(u32, u32),
    // command, selected job
    CommandJobSteps(u32, u32, Vec<u32>), // command, job, selected steps
}

impl Default for Opens {
    fn default() -> Self {
        Self::None
    }
}

#[derive(Debug)]
pub enum CommandError {
    UnknownCommand(u32),
    UnknownJob(u32),
    UnknownSteps(Vec<u32>),
}

impl fmt::Display for CommandError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CommandError::UnknownCommand(cmd_id) => {
                write!(f, "Invariant violation, command_id={} is unknown", cmd_id)
            }
            CommandError::UnknownJob(job_id) => {
                write!(f, "Invariant violation, job_id={} is unknown", job_id)
            }
            CommandError::UnknownSteps(step_ids) => {
                write!(f, "Invariant violation, some of some_step_ids={:?} is unknown", step_ids)
            }
        }
    }
}

#[derive(Clone, Debug)]
pub enum Input {
    Commands(Vec<Arc<Command>>),
    Ids(Vec<u32>),
}

#[derive(Default, Debug)]
pub struct Model {
    pub commands_cancel: Option<oneshot::Sender<()>>,
    pub commands_loading: bool,
    pub commands: Vec<Arc<Command>>,

    pub jobs_cancel: Option<oneshot::Sender<()>>,
    pub jobs_loading: bool,
    pub jobs: Vec<Arc<Job0>>,
    pub jobs_children: HashMap<u32, Vec<u32>>,

    pub steps_cancel: Option<oneshot::Sender<()>>,
    pub steps_loading: bool,
    pub steps: Vec<Arc<Step>>,

    pub opens: Opens,
    pub modal: modal::Model,
}

/// `Msg::FireCommands(..)` adds new commands to the polling list
/// `Msg::Fetch` spawns a future to make the api call
/// `Msg::Fetched(..)` wraps the result like
/// ```norun
/// { "meta": { .. }, "objects": [ cmd0, cmd1, ..., cmd9 ] }
/// ```
#[derive(Clone, Debug)]
pub enum Msg {
    Modal(modal::Msg),
    FireCommands(Input),
    FetchTree,
    FetchedCommands(Box<fetch::ResponseDataResult<ApiList<Command>>>),
    FetchedJobs(Box<fetch::ResponseDataResult<ApiList<Job0>>>),
    FetchedSteps(Box<fetch::ResponseDataResult<ApiList<Step>>>),
    Open(u32),
    Close(u32),
    Noop,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    // log!("command_modal::update", msg);
    match msg {
        Msg::Modal(msg) => {
            modal::update(msg, &mut model.modal, &mut orders.proxy(Msg::Modal));
        }
        Msg::FireCommands(cmds) => {
            model.modal.open = true;

            match cmds {
                Input::Commands(cmds) => {
                    // use the (little) optimization: if the commands all finished,
                    // then don't fetch anything
                    model.commands = cmds;
                    if !is_all_finished(&model.commands) {
                        orders.send_msg(Msg::FetchTree);
                    }
                }
                Input::Ids(ids) => {
                    // we have ids only, so we need to populate the vector first
                    model.commands_loading = true;
                    orders.perform_cmd(fetch_the_batch(ids, |x| Msg::FetchedCommands(Box::new(x))));
                }
            }
        }
        Msg::FetchTree => {
            model.commands_cancel = None;
            if !is_all_finished(&model.commands) {
                schedule_fetch_tree(model, orders);
                //let ids = model.commands.iter().map(|x| x.id).collect();
                // orders
                //     .skip()
                //     .perform_cmd(fetch_the_batch(ids, |x| Msg::FetchedCommands(Box::new(x))));
            }
        }
        Msg::FetchedCommands(cmd_status_result) => {
            model.commands_loading = false;
            match *cmd_status_result {
                Ok(api_list) => {
                    model.commands = api_list.objects.into_iter().map(Arc::new).collect();
                }
                Err(e) => {
                    error!("Failed to perform fetch_command_status {:#?}", e);
                    orders.skip();
                }
            }
            if !is_all_finished(&model.commands) {
                let (cancel, fut) = sleep_with_handle(POLL_INTERVAL, Msg::FetchTree, Msg::Noop);
                model.commands_cancel = Some(cancel);
                orders.perform_cmd(fut);
            }
        }
        Msg::FetchedJobs(job_status_result) => {
            model.jobs_loading = false;
            match *job_status_result {
                Ok(api_list) => {
                    model.jobs = api_list.objects.into_iter().map(Arc::new).collect();
                }
                Err(e) => {
                    error!("Failed to perform fetch_job_status {:#?}", e);
                    orders.skip();
                }
            }
        }
        Msg::FetchedSteps(step_status_result) => {
            model.steps_loading = false;
            match *step_status_result {
                Ok(api_list) => {
                    model.steps = api_list.objects.into_iter().map(Arc::new).collect();
                }
                Err(e) => {
                    error!("Failed to perform fetch_job_status {:#?}", e);
                    orders.skip();
                }
            }
        }
        Msg::Open(x) => {
            model.opens = Opens::Command(x);
        }
        Msg::Close(_x) => {
            model.opens = Opens::None;
        }
        Msg::Noop => {}
    }
}

fn schedule_fetch_tree(model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) -> Result<(), CommandError> {
    match &model.opens {
        Opens::None => {
            // the user has all the commands dropdowns closed
            let ids = model.commands.iter().map(|c| c.id).collect();
            orders
                .skip()
                .perform_cmd(fetch_the_batch(ids, |x| Msg::FetchedCommands(Box::new(x))));
            Ok(())
        }
        Opens::Command(cmd_id) => {
            // the user has opened the info on the command
            if let Some(i) = model.commands.iter().position(|c| c.id == *cmd_id) {
                let cmd_ids: Vec<u32> = model.commands.iter().map(|c| c.id).collect();
                let job_ids: Vec<u32> = model.commands[i]
                    .jobs
                    .iter()
                    .filter_map(|s| extract_uri_id::<Job0>(s))
                    .collect();
                orders
                    .skip()
                    .perform_cmd(fetch_the_batch(cmd_ids, |x| Msg::FetchedCommands(Box::new(x))))
                    .perform_cmd(fetch_the_batch(job_ids, |x| Msg::FetchedJobs(Box::new(x))));
                Ok(())
            } else {
                Err(CommandError::UnknownCommand(*cmd_id))
            }
        }
        Opens::CommandJob(cmd_id, job_id) => {
            // the user has opened the info on the command and selected the corresponding job
            if let Some(i1) = model.commands.iter().position(|c| c.id == *cmd_id) {
                if let Some(i2) = model.jobs.iter().position(|j| j.id == *job_id) {
                    let cmd_ids: Vec<u32> = model.commands.iter().map(|c| c.id).collect();
                    let job_ids: Vec<u32> = model.commands[i1]
                        .jobs
                        .iter()
                        .filter_map(|s| extract_uri_id::<Job0>(s))
                        .collect();
                    let step_ids: Vec<u32> = model.jobs[i2]
                        .steps
                        .iter()
                        .filter_map(|s| extract_uri_id::<Step>(s))
                        .collect();
                    orders
                        .skip()
                        .perform_cmd(fetch_the_batch(cmd_ids, |x| Msg::FetchedCommands(Box::new(x))))
                        .perform_cmd(fetch_the_batch(job_ids, |x| Msg::FetchedJobs(Box::new(x))))
                        .perform_cmd(fetch_the_batch(step_ids, |x| Msg::FetchedSteps(Box::new(x))));
                    Ok(())
                } else {
                    Err(CommandError::UnknownJob(*job_id))
                }
            } else {
                Err(CommandError::UnknownCommand(*cmd_id))
            }
        }
        Opens::CommandJobSteps(cmd_id, job_id, some_step_ids) => {
            // the user has opened the info on the command, selected a job and expanded some of the steps
            if let Some(i1) = model.commands.iter().position(|c| c.id == *cmd_id) {
                if let Some(i2) = model.jobs.iter().position(|j| j.id == *job_id) {
                    let step_ids: HashSet<u32> = model.jobs[i2]
                        .steps
                        .iter()
                        .filter_map(|s| extract_uri_id::<Step>(s))
                        .collect();
                    if some_step_ids.iter().all(|id| step_ids.contains(id)) {
                        let cmd_ids: Vec<u32> = model.commands.iter().map(|c| c.id).collect();
                        let job_ids: Vec<u32> = model.commands[i1]
                            .jobs
                            .iter()
                            .filter_map(|s| extract_uri_id::<Job0>(s))
                            .collect();
                        let the_step_ids = some_step_ids.clone();
                        orders
                            .skip()
                            .perform_cmd(fetch_the_batch(cmd_ids, |x| Msg::FetchedCommands(Box::new(x))))
                            .perform_cmd(fetch_the_batch(job_ids, |x| Msg::FetchedJobs(Box::new(x))))
                            .perform_cmd(fetch_the_batch(the_step_ids, |x| Msg::FetchedSteps(Box::new(x))));
                        Ok(())
                    } else {
                        Err(CommandError::UnknownSteps(some_step_ids.clone()))
                    }
                } else {
                    Err(CommandError::UnknownJob(*job_id))
                }
            } else {
                Err(CommandError::UnknownCommand(*cmd_id))
            }
        }
    }
}

async fn fetch_the_batch<T, F, U>(ids: Vec<u32>, conv: F) -> Result<U, U>
where
    T: DeserializeOwned + EndpointName + 'static,
    F: FnOnce(ResponseDataResult<ApiList<T>>) -> U,
    U: 'static,
{
    // e.g. GET /api/something/?id__in=1&id__in=2&id__in=11&limit=0
    let err_msg = format!("Bad query for {}: {:?}", T::endpoint_name(), ids);
    let mut ids: Vec<_> = ids.into_iter().map(|x| ("id__in", x)).collect();
    ids.push(("limit", 0));
    Request::api_query(T::endpoint_name(), &ids)
        .expect(&err_msg)
        .fetch_json_data(conv)
        .await
}

fn extract_uri_id<T: EndpointName>(input: &str) -> Option<u32> {
    lazy_static::lazy_static! {
        static ref RE: Regex = Regex::new(r"/api/(\w+)/(\d+)/").unwrap();
    }
    RE.captures(input).and_then(|cap: Captures| {
        let s = cap.get(1).unwrap().as_str();
        let t = cap.get(2).unwrap().as_str();
        if s == T::endpoint_name() {
            t.parse::<u32>().ok()
        } else {
            None
        }
    })
}

const fn is_finished(cmd: &Command) -> bool {
    cmd.complete
}

fn is_all_finished(cmds: &[Arc<Command>]) -> bool {
    cmds.iter().all(|cmd| is_finished(cmd))
}

fn is_command_in_opens(cmd_id: u32, opens: &Opens) -> bool {
    match opens {
        Opens::None => false,
        Opens::Command(cid) => cmd_id == *cid,
        Opens::CommandJob(cid, _) => cmd_id == *cid,
        Opens::CommandJobSteps(cid, _, _) => cmd_id == *cid,
    }
}

pub(crate) fn view(model: &Model) -> Node<Msg> {
    if !model.modal.open {
        empty![]
    } else {
        modal::bg_view(
            true,
            Msg::Modal,
            modal::content_view(
                Msg::Modal,
                if model.commands_loading {
                    vec![
                        modal::title_view(Msg::Modal, span!["Loading Command"]),
                        div![
                            class![C.my_12, C.text_center, C.text_gray_500],
                            font_awesome(class![C.w_12, C.h_12, C.inline, C.pulse], "spinner")
                        ],
                        modal::footer_view(vec![close_button()]).merge_attrs(class![C.pt_8]),
                    ]
                } else {
                    vec![
                        modal::title_view(Msg::Modal, plain!["Commands"]),
                        div![
                            class![C.py_8],
                            model
                                .commands
                                .iter()
                                .map(|x| { command_item_view(x, is_command_in_opens(x.id, &model.opens)) })
                        ],
                        modal::footer_view(vec![close_button()]).merge_attrs(class![C.pt_8]),
                    ]
                },
            ),
        )
        .with_listener(keyboard_ev(Ev::KeyDown, move |ev| match ev.key_code() {
            key_codes::ESC => Msg::Modal(modal::Msg::Close),
            _ => Msg::Noop,
        }))
        .merge_attrs(class![C.text_black])
    }
}

fn command_item_view(x: &Command, is_open: bool) -> Node<Msg> {
    let border = if !is_open {
        C.border_transparent
    } else if x.cancelled {
        C.border_gray_500
    } else if x.errored {
        C.border_red_500
    } else if x.complete {
        C.border_green_500
    } else {
        C.border_transparent
    };

    let (open_icon, m) = if is_open {
        ("chevron-circle-up", Msg::Close(x.id))
    } else {
        ("chevron-circle-down", Msg::Open(x.id))
    };

    div![
        class![C.border_b, C.last__border_b_0],
        div![
            class![
                border,
                C.border_l_2,
                C.px_2
                C.py_5,
                C.text_gray_700,
            ],
            header![
                class![
                    C.flex,
                    C.justify_between,
                    C.items_center,
                    C.cursor_pointer,
                    C.select_none,
                    C.py_5
                ],
                simple_ev(Ev::Click, m),
                span![class![C.font_thin, C.text_xl], status_icon(x), &x.message],
                font_awesome(
                    class![C.w_4, C.h_4, C.inline, C.text_gray_700, C.text_blue_500],
                    open_icon
                ),
            ],
            ul![
                class![C.pl_8, C.hidden => !is_open],
                li![class![C.pb_2], "Started at: ", x.created_at],
                li![class![C.pb_2], "Status: ", status_text(x)],
            ]
        ]
    ]
}

fn status_text(cmd: &Command) -> &'static str {
    if cmd.cancelled {
        "Cancelled"
    } else if cmd.errored {
        "Errored"
    } else if cmd.complete {
        "Complete"
    } else {
        "Running"
    }
}

fn status_icon<T>(cmd: &Command) -> Node<T> {
    let cls = class![C.w_4, C.h_4, C.inline, C.mr_4];

    if cmd.cancelled {
        font_awesome(cls, "ban").merge_attrs(class![C.text_gray_500])
    } else if cmd.errored {
        font_awesome(cls, "bell").merge_attrs(class![C.text_red_500])
    } else if cmd.complete {
        font_awesome(cls, "check").merge_attrs(class![C.text_green_500])
    } else {
        font_awesome(cls, "spinner").merge_attrs(class![C.text_gray_500, C.pulse])
    }
}

fn close_button() -> Node<Msg> {
    seed::button![
        class![
            C.bg_transparent,
            C.py_2,
            C.px_4,
            C.rounded_full,
            C.text_blue_500,
            C.hover__bg_gray_100,
            C.hover__text_blue_400,
        ],
        simple_ev(Ev::Click, modal::Msg::Close),
        "Close",
    ]
    .map_msg(Msg::Modal)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_job() {
        assert_eq!(extract_uri_id::<Job0>("/api/job/39/"), Some(39));
        assert_eq!(extract_uri_id::<Step>("/api/step/123/"), Some(123));
        assert_eq!(extract_uri_id::<Command>("/api/command/12/"), Some(12));
        assert_eq!(extract_uri_id::<Command>("/api/xxx/1/"), None);
    }
}
