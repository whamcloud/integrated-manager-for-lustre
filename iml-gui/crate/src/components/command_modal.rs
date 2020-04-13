// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{
        dependency_tree::{DependencyDAG, Deps},
        font_awesome, modal,
    },
    extensions::{MergeAttrs as _, NodeExt as _, RequestExt as _},
    generated::css_classes::C,
    key_codes, sleep_with_handle, GMsg,
};
use futures::channel::oneshot;
use iml_wire_types::{ApiList, Command, EndpointName, Job, Step};
use regex::{Captures, Regex};
use seed::{prelude::*, *};
use serde::de::DeserializeOwned;
use std::collections::HashSet;
use std::fmt;
use std::{sync::Arc, time::Duration};
use crate::components::dependency_tree::{build_direct_dag, build_inverse_dag};

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

#[derive(Debug, Clone)]
pub struct Context {
    pub visited: HashSet<u32>,
    pub is_new: bool,
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
    pub jobs_dag: DependencyDAG<Job0>,
    pub is_dag_inverse: bool,

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
        Msg::FireCommands(ref cmds) => format!("Msg-FireCommands: {:?}", cmds),
        Msg::FetchTree => "Msg-FetchTree".to_string(),
        Msg::FetchedCommands(_) => "Msg-FetchedCommands".to_string(),
        Msg::FetchedJobs(_) => "Msg-FetchedJobs".to_string(),
        Msg::FetchedSteps(_) => "Msg-FetchedSteps".to_string(),
        Msg::Open(_) => "Msg-Open".to_string(),
        Msg::Close(_) => "Msg-Close".to_string(),
        Msg::Noop => "Msg-Noop".to_string(),
    };
    log!("command_modal::update: ", msg_str);

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
                let _ = schedule_fetch_tree(model, orders).map_err(|e| error!(e.to_string()));
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
                    if are_jobs_consistent(&model, &api_list.objects) {
                        model.jobs_loading = false;
                        if model.is_dag_inverse {
                            model.jobs_dag = build_inverse_dag(&api_list.objects);
                        } else {
                            model.jobs_dag = build_direct_dag(&api_list.objects);
                        }
                        model.jobs = api_list.objects.into_iter().map(Arc::new).collect();
                    }
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
            model.opens = perform_open_click(&model.opens, the_id);
            let _ = schedule_fetch_tree(model, orders).map_err(|e| error!(e.to_string()));
        }
        Msg::Close(the_id) => {
            model.opens = perform_close_click(&model.opens, the_id);
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
                let job_ids: Vec<u32> = extract_ids::<Job0>(&model.commands[i].jobs);
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
                    let job_ids: Vec<u32> = extract_ids::<Job0>(&model.commands[i1].jobs);
                    let step_ids: Vec<u32> = extract_ids::<Step>(&model.jobs[i2].steps);
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

fn are_jobs_consistent(model: &Model, jobs: &[Job0]) -> bool {
    let check = |cid: u32| {
        if let Some(cmd) = model.commands.iter().find(|cmd| cmd.id == cid) {
            let cmd_job_ids = extract_ids::<Job0>(&cmd.jobs);
            let jobs_ids = jobs.iter().map(|j| j.id).collect::<Vec<u32>>();
            // the order are guaranteed to be the same
            cmd_job_ids == jobs_ids
        } else {
            false
        }
    };
    match model.opens {
        Opens::None => true,
        Opens::Command(cid) => check(cid),
        Opens::CommandJob(cid, _) => check(cid),
        Opens::CommandJobSteps(cid, _, _) => check(cid),
    }
}

fn is_command_in_opens(cmd_id: u32, opens: &Opens) -> bool {
    match opens {
        Opens::None => false,
        Opens::Command(cid) => cmd_id == *cid,
        Opens::CommandJob(cid, _) => cmd_id == *cid,
        Opens::CommandJobSteps(cid, _, _) => cmd_id == *cid,
    }
}

fn perform_open_click(cur_opens: &Opens, the_id: TypedId) -> Opens {
    match the_id {
        TypedId::Command(cmd_id) => Opens::Command(cmd_id),
        TypedId::Job(job_id) => match &cur_opens {
            Opens::None => cur_opens.clone(),
            Opens::Command(cmd_id_0) => Opens::CommandJob(*cmd_id_0, job_id),
            Opens::CommandJob(cmd_id_0, _) => Opens::CommandJob(*cmd_id_0, job_id),
            Opens::CommandJobSteps(cmd_id_0, _, _) => Opens::CommandJob(*cmd_id_0, job_id),
        },
        TypedId::Step(step_id) => match &cur_opens {
            Opens::None => cur_opens.clone(),
            Opens::Command(_) => cur_opens.clone(),
            Opens::CommandJob(cmd_id_0, job_id_0) => Opens::CommandJobSteps(*cmd_id_0, *job_id_0, vec![step_id]),
            Opens::CommandJobSteps(cmd_id_0, job_id_0, step_ids_0) => {
                if step_ids_0.contains(&step_id) {
                    Opens::CommandJobSteps(*cmd_id_0, *job_id_0, step_ids_0.clone())
                } else {
                    let mut step_ids = step_ids_0.clone();
                    step_ids.push(step_id);
                    Opens::CommandJobSteps(*cmd_id_0, *job_id_0, step_ids)
                }
            }
        },
    }
}

fn perform_close_click(cur_opens: &Opens, the_id: TypedId) -> Opens {
    match the_id {
        TypedId::Command(_cmd_id) => Opens::None,
        TypedId::Job(job_id) => match &cur_opens {
            Opens::None => cur_opens.clone(),
            Opens::Command(_cmd_id_0) => cur_opens.clone(),
            Opens::CommandJob(cmd_id_0, job_id_0) => {
                if job_id == *job_id_0 {
                    Opens::Command(cmd_id_0.clone())
                } else {
                    cur_opens.clone()
                }
            }
            Opens::CommandJobSteps(cmd_id_0, job_id_0, _) => {
                if job_id == *job_id_0 {
                    Opens::Command(cmd_id_0.clone())
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
                let step_ids = step_ids_0.iter().map(|r| *r).filter(|sid| *sid != step_id).collect();
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
                                .map(|x| { command_item_view(x, is_command_in_opens(x.id, &model.opens), &model) })
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

fn command_item_view(x: &Command, is_open: bool, model: &Model) -> Node<Msg> {
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

    let (open_icon, msg) = if is_open {
        ("chevron-circle-up", Msg::Close(TypedId::Command(x.id)))
    } else {
        ("chevron-circle-down", Msg::Open(TypedId::Command(x.id)))
    };
    let job_tree = job_tree_view(&model);
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
                simple_ev(Ev::Click, msg),
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
                li![job_tree],
            ]
        ]
    ]
}

pub fn job_tree_view(model: &Model) -> Node<Msg> {
    div![
        class![C.box_border, C.font_ordinary, C.text_gray_700],
        h4![ class![C.text_lg, C.font_medium], "Jobs" ],
        div![
            class![C.p_1, C.pb_2, C.mb_1, C.bg_gray_100, C.border, C.rounded, C.shadow_sm, C.overflow_auto, C.max_h_screen],
            build_dag_view(&model.jobs_dag, &job_node_view),
        ]
    ]
}

pub fn build_dag_view<T, F>(dag: &DependencyDAG<T>, node_view: &F) -> Node<Msg>
where
    T: Deps,
    F: Fn(Arc<T>, &mut Context) -> Node<Msg>,
{
    fn build_node_view<T, F>(dag: &DependencyDAG<T>, node_view: &F, n: Arc<T>, ctx: &mut Context) -> Node<Msg>
    where
        T: Deps,
        F: Fn(Arc<T>, &mut Context) -> Node<Msg>,
    {
        ctx.is_new = ctx.visited.insert(n.id());
        let parent: Node<Msg> = node_view(Arc::clone(&n), ctx);
        let mut acc: Vec<Node<Msg>> = Vec::new();
        if let Some(deps) = dag.deps.get(&n.id()) {
            if ctx.is_new {
                for d in deps {
                    let rec_node = build_node_view(dag, node_view, Arc::clone(d), ctx);
                    // all the dependencies are shifted with the indent
                    acc.push(rec_node.merge_attrs(class![ C.ml_3, C.mt_1 ]));
                }
            }
        }
        if !parent.is_empty() {
            div![ parent, acc ]
        } else {
            // to remove redundant empty dom elements
            empty!()
        }
    }
    let mut ctx = Context {
        visited: HashSet::new(),
        is_new: false,
    };
    let mut acc: Vec<Node<Msg>> = Vec::with_capacity(dag.roots.len());
    for r in &dag.roots {
        acc.push(build_node_view(dag, &node_view, Arc::clone(r), &mut ctx));
    }
    div![ acc ]
}

fn job_node_view(job: Arc<Job0>, ctx: &mut Context) -> Node<Msg> {
    if ctx.is_new {
        let awesome_style = class![C.fill_current, C.w_4, C.h_4, C.inline];
        let (border, icon) = if job.cancelled {
            (C.border_gray_500, font_awesome(awesome_style, "ban").merge_attrs(class![C.text_red_500]))
        } else if job.errored {
            (C.border_red_500, font_awesome(awesome_style, "exclamation").merge_attrs(class![C.text_red_500]))
        } else if job.state == "complete" {
            (C.border_green_500, font_awesome(awesome_style, "check").merge_attrs(class![C.text_green_500]))
        } else {
            (C.border_transparent, font_awesome(awesome_style, "spinner").merge_attrs(class![C.text_gray_500, C.pulse]))
        };

        if job.steps.is_empty() {
            span![
                span![ class![C.mr_1], icon ],
                span![ job.description ],
                span![ class![C.ml_1, C.text_gray_500], format!("({})", job.id) ],
            ]
        } else {
            a![
                span![ class![C.mr_1], icon ],
                span![ job.description ],
                span![ class![C.ml_1, C.text_gray_500], format!("({})", job.id) ],
                simple_ev(Ev::Click, Msg::Open(TypedId::Job(job.id))),
            ]
        }
    } else {
        empty!()
    }
}


fn step_list_view(is_open: bool) -> Node<Msg> {
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
    use crate::components::dependency_tree::{build_direct_dag, DependencyDAG};
    use std::collections::HashSet;

    #[test]
    fn parse_job() {
        assert_eq!(extract_uri_id::<Job0>("/api/job/39/"), Some(39));
        assert_eq!(extract_uri_id::<Step>("/api/step/123/"), Some(123));
        assert_eq!(extract_uri_id::<Command>("/api/command/12/"), Some(12));
        assert_eq!(extract_uri_id::<Command>("/api/xxx/1/"), None);
    }

    #[test]
    fn build_dependency_dom() {
        let jobs = vec![
            make_job(1, &[2, 3], "One"),
            make_job(2, &[], "Two"),
            make_job(3, &[], "Three"),
        ];
        let dag = build_direct_dag(&jobs);
        let dom = build_dag_view(&dag, &job_node_view);
        let awesome_style = class![C.fill_current, C.w_4, C.h_4, C.inline, C.text_green_500];
        let icon = font_awesome(awesome_style, "check");
        let expected_dom: Node<Msg> = div! [
            div![
                // class![ C.ml_3, C.mt_1 ],
                a![
                    span![ class![C.mr_1], icon.clone() ],
                    span![ "One" ],
                    span![ class![C.ml_1, C.text_gray_500], "(1)" ],
                    simple_ev(Ev::Click, Msg::Open(TypedId::Job(1))),
                ],
                div![
                    class![ C.ml_3, C.mt_1 ],
                    a![
                        span![ class![C.mr_1], icon.clone() ],
                        span![ "Two" ],
                        span![ class![C.ml_1, C.text_gray_500], "(2)" ],
                        simple_ev(Ev::Click, Msg::Open(TypedId::Job(2))),
                    ],
                ],
                div![
                    class![ C.ml_3, C.mt_1 ],
                    a![
                        span![ class![C.mr_1], icon.clone() ],
                        span![ "Three" ],
                        span![ class![C.ml_1, C.text_gray_500], "(3)" ],
                        simple_ev(Ev::Click, Msg::Open(TypedId::Job(3))),
                    ]
                ],
            ],
        ];
        // FIXME It seems there is no any other way, https://github.com/seed-rs/seed/issues/414
        assert_eq!(format!("{:#?}", dom), format!("{:#?}", expected_dom));
    }

    fn make_job(id: u32, deps: &[u32], descr: &str) -> Job0 {
        Job0 {
            available_transitions: vec![],
            cancelled: false,
            class_name: "".to_string(),
            commands: vec!["/api/command/111/".to_string()],
            created_at: "2020-03-16T07:22:34.491600".to_string(),
            description: descr.to_string(),
            errored: false,
            id,
            modified_at: "".to_string(),
            read_locks: vec![],
            resource_uri: format!("/api/job/{}/", id),
            state: "complete".to_string(),
            step_results: Default::default(),
            steps: vec![
                "/api/step/11/".to_string(),
                "/api/step/12/".to_string(),
                "/api/step/13/".to_string(),
            ],
            wait_for: deps.iter().map(|x| format!("/api/job/{}/", x)).collect(),
            write_locks: vec![],
        }
    }
}
