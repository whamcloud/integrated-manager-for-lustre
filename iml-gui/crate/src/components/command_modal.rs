// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{dependency_tree::Deps, font_awesome, modal},
    extensions::{MergeAttrs as _, NodeExt as _, RequestExt as _},
    generated::css_classes::C,
    key_codes, sleep_with_handle, GMsg,
};
use futures::channel::oneshot;
use iml_wire_types::{ApiList, Command, EndpointName, Job, Step};
use regex::{Captures, Regex};
use seed::{prelude::*, *};
use serde::de::DeserializeOwned;
use std::fmt;
use std::{sync::Arc, time::Duration};

/// The component polls `/api/command/` endpoint and this constant defines how often it does.
const POLL_INTERVAL: Duration = Duration::from_millis(1000);

type Job0 = Job<Option<()>>;

impl Deps for Job0 {
    fn id(&self) -> u32 {
        self.id
    }
    fn deps(&self) -> Vec<u32> {
        let mut deps: Vec<u32> = self
            .wait_for
            .iter()
            .filter_map(|s| extract_uri_id::<Job0>(&s))
            .collect();
        deps.sort();
        deps
    }
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum TypedId {
    Command(u32),
    Job(u32),
    Step(u32),
}

#[derive(Clone, Debug)]
pub enum Opens {
    None,
    Command(u32),
    CommandJob(u32, u32),
    CommandJobSteps(u32, u32, Vec<u32>),
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
            CommandError::UnknownCommand(cmd_id) => write!(f, "Invariant violation, command_id={} is unknown", cmd_id),
            CommandError::UnknownJob(job_id) => write!(f, "Invariant violation, job_id={} is unknown", job_id),
            CommandError::UnknownSteps(step_ids) => write!(
                f,
                "Invariant violation, some of some_step_ids={:?} is unknown",
                step_ids
            ),
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
    pub tree_cancel: Option<oneshot::Sender<()>>,

    pub commands_loading: bool,
    pub commands: Vec<Arc<Command>>,

    pub jobs_loading: bool,
    pub jobs: Vec<Arc<Job0>>,

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
    Open(TypedId),
    Close(TypedId),
    Noop,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    let msg_str = match msg {
        Msg::Modal(_) => "Msg-Modal".to_string(),
        Msg::FireCommands(_) => "Msg-FireCommands".to_string(),
        Msg::FetchTree => "Msg-FetchTree".to_string(),
        Msg::FetchedCommands(_) => "Msg-FetchedCommands".to_string(),
        Msg::FetchedJobs(_) => "Msg-FetchedJobs".to_string(),
        Msg::FetchedSteps(_) => "Msg-FetchedSteps".to_string(),
        Msg::Open(_) => "Msg-Open".to_string(),
        Msg::Close(_) => "Msg-Close".to_string(),
        Msg::Noop => "Msg-Noop".to_string(),
    };
    log!("command_modal::update: ", msg_str, model);
    match msg {
        Msg::Modal(msg) => {
            modal::update(msg, &mut model.modal, &mut orders.proxy(Msg::Modal));
        }
        Msg::FireCommands(cmds) => {
            model.opens = Opens::None;
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
            model.tree_cancel = None;
            if !is_all_finished(&model.commands) {
                schedule_fetch_tree(model, orders).map_err(|e| error!(e.to_string()));
            }
        }
        Msg::FetchedCommands(commands_data_result) => {
            model.commands_loading = false;
            match *commands_data_result {
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
                model.tree_cancel = Some(cancel);
                orders.perform_cmd(fut);
            }
        }
        Msg::FetchedJobs(jobs_data_result) => {
            match *jobs_data_result {
                Ok(api_list) => {
                    // check that api_list.objects are consistent with the commands
                    // if
                    model.jobs = api_list.objects.into_iter().map(Arc::new).collect();
                }
                Err(e) => {
                    model.jobs_loading = false;
                    error!("Failed to perform fetch_job_status {:#?}", e);
                    orders.skip();
                }
            }
        }
        Msg::FetchedSteps(steps_data_result) => {
            model.steps_loading = false;
            match *steps_data_result {
                Ok(api_list) => {
                    model.steps = api_list.objects.into_iter().map(Arc::new).collect();
                }
                Err(e) => {
                    error!("Failed to perform fetch_job_status {:#?}", e);
                    orders.skip();
                }
            }
        }
        Msg::Open(the_id) => {
            model.opens = perform_open_click(&model.opens, &the_id);
        }
        Msg::Close(the_id) => {
            model.opens = perform_close_click(&model.opens, &the_id);
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
                // NOTE: we can try to use future::select_all(futs.into_iter()) here
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
                    let step_ids = extract_ids::<Step>(&model.jobs[i2].steps);
                    if some_step_ids.iter().all(|id| step_ids.contains(id)) {
                        let cmd_ids = model.commands.iter().map(|c| c.id).collect();
                        let job_ids = extract_ids::<Job0>(&model.commands[i1].jobs);
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

fn extract_ids<T: EndpointName>(uris: &[String]) -> Vec<u32> {
    // uris is the slice of strings like ["/api/step/123/", .. , "/api/step/234/"]
    uris.iter().filter_map(|s| extract_uri_id::<T>(s)).collect()
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

fn is_job_in_opens(job_id: u32, opens: &Opens) -> bool {
    match opens {
        Opens::None => false,
        Opens::Command(_) => false,
        Opens::CommandJob(_, jid) => job_id == *jid,
        Opens::CommandJobSteps(_, jid, _) => job_id == *jid,
    }
}

fn perform_open_click(cur_opens: &Opens, the_id: &TypedId) -> Opens {
    match the_id {
        TypedId::Command(cmd_id) => Opens::Command(*cmd_id),
        TypedId::Job(job_id) => match &cur_opens {
            Opens::None => cur_opens.clone(),
            Opens::Command(cmd_id_0) => Opens::CommandJob(*cmd_id_0, *job_id),
            Opens::CommandJob(cmd_id_0, _) => Opens::CommandJob(*cmd_id_0, *job_id),
            Opens::CommandJobSteps(cmd_id_0, _, _) => Opens::CommandJob(*cmd_id_0, *job_id),
        },
        TypedId::Step(step_id) => match &cur_opens {
            Opens::None => cur_opens.clone(),
            Opens::Command(_) => cur_opens.clone(),
            Opens::CommandJob(cmd_id_0, job_id_0) => Opens::CommandJobSteps(*cmd_id_0, *job_id_0, vec![*step_id]),
            Opens::CommandJobSteps(cmd_id_0, job_id_0, step_ids_0) => {
                if step_ids_0.contains(&step_id) {
                    Opens::CommandJobSteps(*cmd_id_0, *job_id_0, step_ids_0.clone())
                } else {
                    let mut step_ids = step_ids_0.clone();
                    step_ids.push(*step_id);
                    Opens::CommandJobSteps(*cmd_id_0, *job_id_0, step_ids)
                }
            }
        },
    }
}

fn perform_close_click(cur_opens: &Opens, the_id: &TypedId) -> Opens {
    match the_id {
        TypedId::Command(_cmd_id) => Opens::None,
        TypedId::Job(job_id) => match &cur_opens {
            Opens::None => cur_opens.clone(),
            Opens::Command(_cmd_id_0) => cur_opens.clone(),
            Opens::CommandJob(cmd_id_0, job_id_0) => {
                if job_id == job_id_0 {
                    Opens::Command(*cmd_id_0)
                } else {
                    cur_opens.clone()
                }
            }
            Opens::CommandJobSteps(cmd_id_0, job_id_0, _) => {
                if job_id == job_id_0 {
                    Opens::Command(*cmd_id_0)
                } else {
                    cur_opens.clone()
                }
            }
        },
        TypedId::Step(step_id) => match &cur_opens {
            Opens::None => cur_opens.clone(),
            Opens::Command(_) => cur_opens.clone(),
            Opens::CommandJob(_, _) => cur_opens.clone(),
            Opens::CommandJobSteps(cmd_id_0, job_id_0, step_ids_0) => {
                // if the clicked step_id is contained in the list of open steps, just remove it
                let step_ids = step_ids_0.iter().map(|r| *r).filter(|sid| *sid != *step_id).collect();
                Opens::CommandJobSteps(*cmd_id_0, *job_id_0, step_ids)
            }
        },
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
    } else if x.complete {
        C.border_green_500
    } else if x.errored {
        C.border_red_500
    } else if x.cancelled {
        C.border_gray_500
    } else {
        C.border_transparent
    };

    let (open_icon, m) = if is_open {
        ("chevron-circle-up", Msg::Close(TypedId::Command(x.id)))
    } else {
        ("chevron-circle-down", Msg::Open(TypedId::Command(x.id)))
    };

    let job_tree = empty!();

    div![
        attrs! { "cmd__id" => x.id.to_string() }, // todo revert
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
                job_tree,
            ]
        ]
    ]
}

fn job_tree_view(model: &Model, start: u32, children: &[u32]) -> Node<Msg> {
    if children.contains(&start) {
        // normally this should not happen, we check this to avoid potential loop
        empty!()
    } else {
        let jobs = children
            .iter()
            .filter_map(|job_id| model.jobs.iter().find(|job| job.id == *job_id));
        div![
            class![C.mr_4],
            ul![
                class![C.border_4],
                jobs.map(|job| {
                    let children: Vec<u32> = job.wait_for.iter().filter_map(|s| extract_uri_id::<Job0>(s)).collect();
                    li!["Job", job.id.to_string(), job_tree_view(model, start, &children)]
                })
            ]
        ]
    }
}

fn job_item_view(x: &Job0, is_open: bool) -> Node<Msg> {
    let border = if !is_open {
        C.border_transparent
    } else if x.cancelled {
        C.border_gray_500
    } else if x.errored {
        C.border_red_500
    } else if x.state == "complete" {
        C.border_green_500
    } else {
        C.border_transparent
    };

    let (open_icon, m) = if is_open {
        ("chevron-circle-up", Msg::Close(TypedId::Job(x.id)))
    } else {
        ("chevron-circle-down", Msg::Open(TypedId::Job(x.id)))
    };

    div!["job_item_view"]
}

fn step_item_view(x: &Step, is_open: bool) -> Node<Msg> {
    div!["step_item_view"]
}

fn status_text(cmd: &Command) -> &'static str {
    if cmd.complete {
        "Complete"
    } else if cmd.errored {
        "Errored"
    } else if cmd.cancelled {
        "Cancelled"
    } else {
        "Running"
    }
}

fn status_icon<T>(cmd: &Command) -> Node<T> {
    let cls = class![C.w_4, C.h_4, C.inline, C.mr_4];

    if cmd.complete {
        font_awesome(cls, "check").merge_attrs(class![C.text_green_500])
    } else if cmd.cancelled {
        font_awesome(cls, "ban").merge_attrs(class![C.text_gray_500])
    } else if cmd.errored {
        font_awesome(cls, "bell").merge_attrs(class![C.text_red_500])
    } else {
        font_awesome(cls, "spinner").merge_attrs(class![C.text_gray_500, C.pulse])
    }
}

fn close_button() -> Node<Msg> {
    // todo revert
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
    use crate::components::dependency_tree::{build_direct_dag, build_forest, Context, DependencyForest};
    use std::collections::HashSet;

    #[test]
    fn parse_job() {
        assert_eq!(extract_uri_id::<Job0>("/api/job/39/"), Some(39));
        assert_eq!(extract_uri_id::<Step>("/api/step/123/"), Some(123));
        assert_eq!(extract_uri_id::<Command>("/api/command/12/"), Some(12));
        assert_eq!(extract_uri_id::<Command>("/api/xxx/1/"), None);
    }

    pub fn build_tree_dom<T, F>(tree: &DependencyForest<T>, node_to_str: &F) -> Node<Msg>
        where
            T: Deps,
            F: Fn(Arc<T>, &mut Context) -> Node<Msg>,
    {
        fn build_node_str<T, F>(tree: &DependencyForest<T>, node_to_str: &F, n: Arc<T>, ctx: &mut Context) -> Node<Msg>
            where
                T: Deps,
                F: Fn(Arc<T>, &mut Context) -> Node<Msg>,
        {
            empty!()
        }
        //     ctx.is_new = ctx.visited.insert(n.id());
        //     let cap = node_to_str(Arc::clone(&n), ctx);
        //     let list = div![];
        //     let mut node = ul![
        //         cap
        //     ];
        //     if let Some(deps) = tree.deps.get(&n.id()) {
        //         ctx.indent += 1;
        //         if ctx.is_new {
        //             for d in deps {
        //                 res.write_str(&build_node_str(tree, node_to_str, Arc::clone(d), ctx));
        //             }
        //         }
        //         ctx.indent -= 1;
        //     }
        //     res
        // }
        // let mut ctx = Context {
        //     visited: HashSet::new(),
        //     indent: 0,
        //     is_new: false,
        // };
        // let mut res = String::new();
        // for r in &tree.roots {
        //     let _ = build_node_str(tree, node_to_str, Arc::clone(r), &mut ctx);
        // }
        // res
        empty!()
    }


    #[test]
    fn build_node_tree() {
        let api_list: ApiList<Job0> = serde_json::from_str(JOBS).unwrap();
        let forest = build_direct_dag(&api_list.objects);
        let job_to_node = |job: Arc<Job0>, ctx: &mut Context| {
            let ellipsis = if ctx.is_new { class![] } else { class![] };
            let this: Node<Msg> = li![
                class![C.pl_2, C.justify_between, C.items_center],
                div![
                    span![ job.id.to_string() ],
                    a! [
                        class![ C.pointer_events_none ],
                        format!("{}{}", job.description, ellipsis),
                    ]
                ]
            ];
            this
        };
        let node: Node<Msg> = ul! [
            class!["my-class"],
            vec![
                li! ["1"],
                li! ["2"],
                li! ["3"],
            ],
        ];
        println!("{:#?}", node);
        // let cls = class![C.w_4, C.h_4, C.inline, C.mr_4];
        // let li: Node<Msg> = li! [
        //     class![ C.pl_2, C.justify_between, C.items_center ],
        //     font_awesome(cls, "check").merge_attrs(class![C.text_green_500]),
        //     span![ "1" ],
        //     a! [
        //         class![ C.pointer_events_none ],
        //         "Install packages on server oss2.local"
        //     ]
        // ];

    }

    const JOBS: &'static str = r#"{
  "meta": {
    "limit": 20,
    "next": null,
    "offset": 0,
    "previous": null,
    "total_count": 10
  },
  "objects": [
    {
      "available_transitions": [],
      "cancelled": false,
      "class_name": "InstallHostPackagesJob",
      "commands": [
        "/api/command/12/"
      ],
      "created_at": "2020-03-16T07:22:34.491600",
      "description": "Install packages on server oss2.local",
      "errored": false,
      "id": 39,
      "modified_at": "2020-03-16T07:22:34.491573",
      "read_locks": [],
      "resource_uri": "/api/job/39/",
      "state": "complete",
      "step_results": {
        "/api/step/12/": null,
        "/api/step/16/": null,
        "/api/step/20/": null,
        "/api/step/22/": null,
        "/api/step/25/": null
      },
      "steps": [
        "/api/step/12/",
        "/api/step/16/",
        "/api/step/20/",
        "/api/step/22/",
        "/api/step/25/"
      ],
      "wait_for": [],
      "write_locks": [
        {
          "locked_item_content_type_id": 17,
          "locked_item_id": 4,
          "locked_item_uri": "/api/host/4/",
          "resource_uri": ""
        }
      ]
    },
    {
      "available_transitions": [],
      "cancelled": false,
      "class_name": "ConfigureNTPJob",
      "commands": [
        "/api/command/12/"
      ],
      "created_at": "2020-03-16T07:22:34.516793",
      "description": "Configure NTP on oss2.local",
      "errored": false,
      "id": 40,
      "modified_at": "2020-03-16T07:22:34.516760",
      "read_locks": [
        {
          "locked_item_content_type_id": 17,
          "locked_item_id": 4,
          "locked_item_uri": "/api/host/4/",
          "resource_uri": ""
        }
      ],
      "resource_uri": "/api/job/40/",
      "state": "complete",
      "step_results": {
        "/api/step/55/": null,
        "/api/step/57/": null,
        "/api/step/60/": null,
        "/api/step/62/": null,
        "/api/step/63/": null
      },
      "steps": [
        "/api/step/55/",
        "/api/step/57/",
        "/api/step/60/",
        "/api/step/62/",
        "/api/step/63/"
      ],
      "wait_for": [
        "/api/job/39/"
      ],
      "write_locks": [
        {
          "locked_item_content_type_id": 21,
          "locked_item_id": 4,
          "locked_item_uri": "/api/ntp_configuration/4/",
          "resource_uri": ""
        }
      ]
    },
    {
      "available_transitions": [],
      "cancelled": false,
      "class_name": "EnableLNetJob",
      "commands": [
        "/api/command/12/"
      ],
      "created_at": "2020-03-16T07:22:34.554315",
      "description": "Enable LNet on oss2.local",
      "errored": false,
      "id": 41,
      "modified_at": "2020-03-16T07:22:34.554290",
      "read_locks": [
        {
          "locked_item_content_type_id": 17,
          "locked_item_id": 4,
          "locked_item_uri": "/api/host/4/",
          "resource_uri": ""
        }
      ],
      "resource_uri": "/api/job/41/",
      "state": "complete",
      "step_results": {},
      "steps": [],
      "wait_for": [
        "/api/job/39/"
      ],
      "write_locks": [
        {
          "locked_item_content_type_id": 53,
          "locked_item_id": 4,
          "locked_item_uri": "/api/lnet_configuration/4/",
          "resource_uri": ""
        }
      ]
    },
    {
      "available_transitions": [],
      "cancelled": false,
      "class_name": "AutoConfigureCorosync2Job",
      "commands": [
        "/api/command/12/"
      ],
      "created_at": "2020-03-16T07:22:34.591853",
      "description": "Configure Corosync on oss2.local.",
      "errored": false,
      "id": 42,
      "modified_at": "2020-03-16T07:22:34.591829",
      "read_locks": [
        {
          "locked_item_content_type_id": 17,
          "locked_item_id": 4,
          "locked_item_uri": "/api/host/4/",
          "resource_uri": ""
        }
      ],
      "resource_uri": "/api/job/42/",
      "state": "complete",
      "step_results": {
        "/api/step/56/": null
      },
      "steps": [
        "/api/step/56/"
      ],
      "wait_for": [
        "/api/job/39/"
      ],
      "write_locks": [
        {
          "locked_item_content_type_id": 75,
          "locked_item_id": 4,
          "locked_item_uri": "/api/corosync_configuration/4/",
          "resource_uri": ""
        }
      ]
    },
    {
      "available_transitions": [],
      "cancelled": false,
      "class_name": "StartCorosync2Job",
      "commands": [
        "/api/command/12/"
      ],
      "created_at": "2020-03-16T07:22:34.627692",
      "description": "Start Corosync on oss2.local",
      "errored": false,
      "id": 43,
      "modified_at": "2020-03-16T07:22:34.627667",
      "read_locks": [],
      "resource_uri": "/api/job/43/",
      "state": "complete",
      "step_results": {
        "/api/step/74/": null
      },
      "steps": [
        "/api/step/74/"
      ],
      "wait_for": [
        "/api/job/42/"
      ],
      "write_locks": [
        {
          "locked_item_content_type_id": 75,
          "locked_item_id": 4,
          "locked_item_uri": "/api/corosync_configuration/4/",
          "resource_uri": ""
        }
      ]
    },
    {
      "available_transitions": [],
      "cancelled": true,
      "class_name": "LoadLNetJob",
      "commands": [
        "/api/command/12/"
      ],
      "created_at": "2020-03-16T07:22:34.648217",
      "description": "Load the LNet kernel modules.",
      "errored": false,
      "id": 44,
      "modified_at": "2020-03-16T07:22:34.648185",
      "read_locks": [],
      "resource_uri": "/api/job/44/",
      "state": "complete",
      "step_results": {
        "/api/step/58/": null,
        "/api/step/64/": null
      },
      "steps": [
        "/api/step/58/",
        "/api/step/64/"
      ],
      "wait_for": [
        "/api/job/41/"
      ],
      "write_locks": [
        {
          "locked_item_content_type_id": 53,
          "locked_item_id": 4,
          "locked_item_uri": "/api/lnet_configuration/4/",
          "resource_uri": ""
        }
      ]
    },
    {
      "available_transitions": [],
      "cancelled": true,
      "class_name": "StartLNetJob",
      "commands": [
        "/api/command/12/"
      ],
      "created_at": "2020-03-16T07:22:34.672353",
      "description": "Start the LNet networking layer.",
      "errored": false,
      "id": 45,
      "modified_at": "2020-03-16T07:22:34.672291",
      "read_locks": [],
      "resource_uri": "/api/job/45/",
      "state": "complete",
      "step_results": {},
      "steps": [],
      "wait_for": [
        "/api/job/44/"
      ],
      "write_locks": [
        {
          "locked_item_content_type_id": 53,
          "locked_item_id": 4,
          "locked_item_uri": "/api/lnet_configuration/4/",
          "resource_uri": ""
        }
      ]
    },
    {
      "available_transitions": [],
      "cancelled": false,
      "class_name": "ConfigurePacemakerJob",
      "commands": [
        "/api/command/12/"
      ],
      "created_at": "2020-03-16T07:22:34.695375",
      "description": "Configure Pacemaker on oss2.local.",
      "errored": false,
      "id": 46,
      "modified_at": "2020-03-16T07:22:34.695324",
      "read_locks": [
        {
          "locked_item_content_type_id": 17,
          "locked_item_id": 4,
          "locked_item_uri": "/api/host/4/",
          "resource_uri": ""
        },
        {
          "locked_item_content_type_id": 75,
          "locked_item_id": 4,
          "locked_item_uri": "/api/corosync_configuration/4/",
          "resource_uri": ""
        }
      ],
      "resource_uri": "/api/job/46/",
      "state": "complete",
      "step_results": {
        "/api/step/77/": null,
        "/api/step/78/": null,
        "/api/step/82/": null
      },
      "steps": [
        "/api/step/77/",
        "/api/step/78/",
        "/api/step/82/"
      ],
      "wait_for": [
        "/api/job/43/",
        "/api/job/39/"
      ],
      "write_locks": [
        {
          "locked_item_content_type_id": 64,
          "locked_item_id": 4,
          "locked_item_uri": "/api/pacemaker_configuration/4/",
          "resource_uri": ""
        }
      ]
    },
    {
      "available_transitions": [],
      "cancelled": false,
      "class_name": "StartPacemakerJob",
      "commands": [
        "/api/command/12/"
      ],
      "created_at": "2020-03-16T07:22:34.755602",
      "description": "Start Pacemaker on oss2.local",
      "errored": false,
      "id": 47,
      "modified_at": "2020-03-16T07:22:34.755578",
      "read_locks": [
        {
          "locked_item_content_type_id": 75,
          "locked_item_id": 4,
          "locked_item_uri": "/api/corosync_configuration/4/",
          "resource_uri": ""
        }
      ],
      "resource_uri": "/api/job/47/",
      "state": "complete",
      "step_results": {
        "/api/step/85/": null
      },
      "steps": [
        "/api/step/85/"
      ],
      "wait_for": [
        "/api/job/43/",
        "/api/job/46/"
      ],
      "write_locks": [
        {
          "locked_item_content_type_id": 64,
          "locked_item_id": 4,
          "locked_item_uri": "/api/pacemaker_configuration/4/",
          "resource_uri": ""
        }
      ]
    },
    {
      "available_transitions": [],
      "cancelled": true,
      "class_name": "SetupHostJob",
      "commands": [
        "/api/command/12/"
      ],
      "created_at": "2020-03-16T07:22:34.798434",
      "description": "Setup managed host oss2.local",
      "errored": false,
      "id": 48,
      "modified_at": "2020-03-16T07:22:34.798408",
      "read_locks": [
        {
          "locked_item_content_type_id": 53,
          "locked_item_id": 4,
          "locked_item_uri": "/api/lnet_configuration/4/",
          "resource_uri": ""
        },
        {
          "locked_item_content_type_id": 64,
          "locked_item_id": 4,
          "locked_item_uri": "/api/pacemaker_configuration/4/",
          "resource_uri": ""
        },
        {
          "locked_item_content_type_id": 21,
          "locked_item_id": 4,
          "locked_item_uri": "/api/ntp_configuration/4/",
          "resource_uri": ""
        }
      ],
      "resource_uri": "/api/job/48/",
      "state": "complete",
      "step_results": {},
      "steps": [],
      "wait_for": [
        "/api/job/39/",
        "/api/job/40/",
        "/api/job/41/",
        "/api/job/42/",
        "/api/job/45/",
        "/api/job/46/",
        "/api/job/47/"
      ],
      "write_locks": [
        {
          "locked_item_content_type_id": 17,
          "locked_item_id": 4,
          "locked_item_uri": "/api/host/4/",
          "resource_uri": ""
        }
      ]
    }
  ]
}
"#;
}
