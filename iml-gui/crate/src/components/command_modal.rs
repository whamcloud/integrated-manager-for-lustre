// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{font_awesome, modal},
    dependency_tree::{build_direct_dag, DependencyDAG, Deps, Rich},
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

/// The component polls `/api/command/` endpoint and this constant defines how often it does.
const POLL_INTERVAL: Duration = Duration::from_millis(1000);

type Job0 = Job<Option<()>>;

type RichCommand = Rich<u32, Command>;
type RichJob = Rich<u32, Job0>;
type RichStep = Rich<u32, Step>;

type JobsGraph = DependencyDAG<u32, RichJob>;

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum TypedId {
    Command(u32),
    Job(u32),
    Step(u32),
}

#[derive(Clone, Eq, PartialEq, Debug)]
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
            Self::UnknownCommand(cmd_id) => write!(f, "Invariant violation, command_id={} is unknown", cmd_id),
            Self::UnknownJob(job_id) => write!(f, "Invariant violation, job_id={} is unknown", job_id),
            Self::UnknownSteps(step_ids) => write!(
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

    pub commands_loading: bool, // TODO use commands_view instead

    pub commands: Vec<Arc<RichCommand>>,
    pub commands_view: Vec<Arc<RichCommand>>,

    pub jobs: Vec<Arc<RichJob>>,
    pub jobs_view: Vec<Arc<RichJob>>,
    pub jobs_graph: JobsGraph,

    pub steps: Vec<Arc<RichStep>>,
    pub steps_view: Vec<Arc<RichStep>>,

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
    Click(TypedId),
    Noop,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Modal(msg) => {
            modal::update(msg, &mut model.modal, &mut orders.proxy(Msg::Modal));
        }
        Msg::FireCommands(cmds) => {
            model.opens = Opens::None;
            model.modal.open = true;

            // clear model from the previous command modal work
            model.commands.clear();
            model.jobs.clear();
            model.jobs_graph.clear();
            model.steps.clear();

            match cmds {
                Input::Commands(mut cmds) => {
                    // use the (little) optimization:
                    // if we already have the commands and they all finished, we don't need to poll them anymore
                    model.commands = cmds
                        .iter_mut()
                        .map(|ac| Arc::new(RichCommand::new((**ac).clone(), extract_children_from_cmd)))
                        .collect();
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
                if let Err(e) = schedule_fetch_tree(model, orders) {
                    error!(e.to_string())
                }
            }
        }
        Msg::FetchedCommands(commands_data_result) => {
            model.commands_loading = false;
            match *commands_data_result {
                Ok(api_list) => {
                    model.commands = api_list
                        .objects
                        .into_iter()
                        .map(|c| Arc::new(RichCommand::new(c, extract_children_from_cmd)))
                        .collect();
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
        Msg::FetchedJobs(jobs_data_result) => match *jobs_data_result {
            Ok(api_list) => {
                if are_jobs_consistent(model, &api_list.objects) {
                    let jobs_graph_data = api_list
                        .objects
                        .iter()
                        .map(|j| Arc::new(RichJob::new(j.clone(), extract_wait_fors_from_job)))
                        .collect::<Vec<Arc<RichJob>>>();
                    model.jobs = api_list
                        .objects
                        .into_iter()
                        .map(|j| Arc::new(RichJob::new(j, extract_children_from_job)))
                        .collect();
                    model.jobs_graph = build_direct_dag(&jobs_graph_data);
                }
            }
            Err(e) => {
                // TODO model.jobs_loading = false;
                error!("Failed to perform fetch_job_status {:#?}", e);
                orders.skip();
            }
        },
        Msg::FetchedSteps(steps_data_result) => match *steps_data_result {
            Ok(api_list) => {
                if are_steps_consistent(model, &api_list.objects) {
                    // TODO model.steps_loading = false;
                    model.steps = api_list
                        .objects
                        .into_iter()
                        .map(|s| RichStep::new(s, extract_children_from_step))
                        .map(Arc::new)
                        .collect();
                }
            }
            Err(e) => {
                // TODO model.steps_loading = false;
                error!("Failed to perform fetch_job_status {:#?}", e);
                orders.skip();
            }
        },
        Msg::Click(the_id) => {
            let (opens, do_fetch, do_clear) = interpret_click(&model.opens, the_id);
            model.opens = opens;

            if let Some(clear_level) = do_clear {
                if clear_level == 2 {
                    model.jobs.clear();
                    model.jobs_graph.clear();
                    model.steps.clear();
                } else if clear_level == 1 {
                    model.steps.clear();
                }
            }
            if do_fetch {
                if let Err(e) = schedule_fetch_tree(model, orders) {
                    error!(e.to_string())
                }
            }
        }
        Msg::Noop => {}
    }
}

fn schedule_fetch_tree(model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) -> Result<(), CommandError> {
    match &model.opens {
        Opens::None => {
            // the user has all the commands dropdowns closed
            let ids = model.commands.iter().map(|c| c.id).collect::<Vec<u32>>();
            orders
                .skip()
                .perform_cmd(fetch_the_batch(ids, |x| Msg::FetchedCommands(Box::new(x))));
            Ok(())
        }
        Opens::Command(cmd_id) => {
            // the user has opened the info on the command,
            // we need the corresponding jobs to build the dependency graph
            if let Some(i) = model.commands.iter().position(|c| c.id == *cmd_id) {
                let cmd_ids = model.commands.iter().map(|c| c.id).collect::<Vec<u32>>();
                let job_ids = extract_ids::<Job0>(&model.commands[i].jobs);
                orders
                    .skip()
                    .perform_cmd(fetch_the_batch(job_ids, |x| Msg::FetchedJobs(Box::new(x))))
                    .perform_cmd(fetch_the_batch(cmd_ids, |x| Msg::FetchedCommands(Box::new(x))));
                Ok(())
            } else {
                Err(CommandError::UnknownCommand(*cmd_id))
            }
        }
        Opens::CommandJob(cmd_id, job_id) => {
            // the user has opened the info on the command and selected the corresponding job
            if let Some(i1) = model.commands.iter().position(|c| c.id == *cmd_id) {
                if let Some(i2) = model.jobs.iter().position(|j| j.id == *job_id) {
                    let cmd_ids = model.commands.iter().map(|c| c.id).collect::<Vec<u32>>();
                    let job_ids = extract_ids::<Job0>(&model.commands[i1].jobs);
                    let step_ids = extract_ids::<Step>(&model.jobs[i2].steps);
                    orders
                        .skip()
                        .perform_cmd(fetch_the_batch(step_ids, |x| Msg::FetchedSteps(Box::new(x))))
                        .perform_cmd(fetch_the_batch(job_ids, |x| Msg::FetchedJobs(Box::new(x))))
                        .perform_cmd(fetch_the_batch(cmd_ids, |x| Msg::FetchedCommands(Box::new(x))));
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
                        let cmd_ids = model.commands.iter().map(|c| c.id).collect::<Vec<u32>>();
                        let job_ids = extract_ids::<Job0>(&model.commands[i1].jobs);
                        orders
                            .skip()
                            .perform_cmd(fetch_the_batch(some_step_ids.clone(), |x| {
                                Msg::FetchedSteps(Box::new(x))
                            }))
                            .perform_cmd(fetch_the_batch(job_ids, |x| Msg::FetchedJobs(Box::new(x))))
                            .perform_cmd(fetch_the_batch(cmd_ids, |x| Msg::FetchedCommands(Box::new(x))));
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
                            model.commands.iter().map(|x| { command_item_view(model, x) })
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

fn command_item_view(model: &Model, x: &RichCommand) -> Node<Msg> {
    let is_open = is_typed_id_in_opens(&model.opens, TypedId::Command(x.id));
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

    let open_icon = if is_open {
        "chevron-circle-up"
    } else {
        "chevron-circle-down"
    };
    let job_tree = job_tree_view(&model.jobs_graph);
    let step_list = step_list_view(&model.opens, &model.steps);
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
                simple_ev(Ev::Click, Msg::Click(TypedId::Command(x.id))),
                span![class![C.font_thin, C.text_xl], cmd_status_icon(x), &x.message],
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
                li![step_list],
            ]
        ]
    ]
}

pub fn job_tree_view(jobs_graph: &JobsGraph) -> Node<Msg> {
    div![
        class![C.font_ordinary, C.text_gray_700],
        h4![class![C.text_lg, C.font_medium], "Jobs"],
        div![
            class![
                C.p_1,
                C.pb_2,
                C.mb_1,
                C.bg_gray_100,
                C.border,
                C.rounded,
                C.shadow_sm,
                C.overflow_auto,
                C.max_h_screen
            ],
            job_dag_view(jobs_graph, &job_item_view),
        ]
    ]
}

pub fn job_dag_view<F>(dag: &JobsGraph, node_view: &F) -> Node<Msg>
where
    F: Fn(Arc<RichJob>, &mut Context) -> Node<Msg>,
{
    fn build_node_view<F>(dag: &JobsGraph, node_view: &F, n: Arc<RichJob>, ctx: &mut Context) -> Node<Msg>
    where
        F: Fn(Arc<RichJob>, &mut Context) -> Node<Msg>,
    {
        ctx.is_new = ctx.visited.insert(n.id);
        let parent: Node<Msg> = node_view(Arc::clone(&n), ctx);
        let mut acc: Vec<Node<Msg>> = Vec::new();
        if let Some(deps) = dag.deps.get(&n.id()) {
            if ctx.is_new {
                for d in deps {
                    let rec_node = build_node_view(dag, node_view, Arc::clone(d), ctx);
                    // all the dependencies are shifted with the indent
                    acc.push(rec_node.merge_attrs(class![C.ml_3, C.mt_1]));
                }
            }
        }
        if !parent.is_empty() {
            div![parent, acc]
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
    div![acc]
}

fn job_item_view(job: Arc<RichJob>, ctx: &mut Context) -> Node<Msg> {
    if ctx.is_new {
        let icon = job_status_icon(job.as_ref());
        if job.steps.is_empty() {
            span![span![class![C.mr_1], icon], span![job.description]]
        } else {
            a![
                span![class![C.mr_1], icon],
                span![class![C.cursor_pointer, C.underline], job.description],
                simple_ev(Ev::Click, Msg::Click(TypedId::Job(job.id))),
            ]
        }
    } else {
        empty!()
    }
}

fn step_list_view(opens: &Opens, steps: &[Arc<RichStep>]) -> Node<Msg> {
    if steps.is_empty() {
        empty!()
    } else {
        div![ul![
            class![
                C.p_1,
                C.pb_2,
                C.mb_1,
                C.bg_gray_100,
                C.border,
                C.rounded,
                C.shadow_sm,
                C.overflow_auto
            ],
            steps.iter().map(|step| {
                let is_open = is_typed_id_in_opens(opens, TypedId::Step(step.id));
                li![step_item_view(step, is_open)]
            })
        ]]
    }
}

fn step_item_view(step: &RichStep, is_open: bool) -> Vec<Node<Msg>> {
    let icon = step_status_icon(step, is_open);
    let item_caption = div![
        class![C.flex],
        div![attrs![At::Style => "flex: 0 0 1em"], class![C.mx_2], icon],
        div![
            class![C.flex_grow, C.cursor_pointer, C.underline],
            step.class_name,
            simple_ev(Ev::Click, Msg::Click(TypedId::Step(step.id))),
        ],
    ];
    let item_body = if !is_open {
        empty!()
    } else {
        // note, we cannot just use the Debug instance for step.args,
        // because the keys order changes every time the HashMap is traversed
        let mut arg_keys = step.args.keys().collect::<Vec<&String>>();
        arg_keys.sort();
        let mut arg_str = String::with_capacity(step.args.len() * 10);
        for k in arg_keys {
            arg_str.push_str(k);
            arg_str.push_str(": ");
            arg_str.push_str(&format!(
                "{}\n",
                step.args.get(k).unwrap_or(&serde_json::value::Value::Null)
            ));
        }
        let pre_class = class![
            C.p_2, C.m_2
            C.leading_tight,
            C.text_gray_100,
            C.bg_gray_900,
            C.overflow_x_hidden,
            C.whitespace_pre_line,
            C.break_all,
        ];
        div![
            class![C.flex],
            div![
                attrs![At::Style => "flex: 0 0 1em"],
                class![C.border_r_2, C.border_gray_300, C.hover__border_gray_600],
                simple_ev(Ev::Click, Msg::Click(TypedId::Step(step.id))),
            ],
            div![attrs![At::Style => "flex: 0 0 1em"],],
            div![
                class![C.float_right, C.flex_grow],
                h4![class![C.text_lg, C.font_medium], "Arguments"],
                pre![&pre_class, arg_str],
                if step.console.is_empty() {
                    vec![]
                } else {
                    vec![
                        h4![class![C.text_lg, C.font_medium], "Logs"],
                        pre![&pre_class, step.console],
                    ]
                }
            ]
        ]
    };
    vec![item_caption, item_body]
}

fn status_text(cmd: &RichCommand) -> &'static str {
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

fn cmd_status_icon<T>(cmd: &RichCommand) -> Node<T> {
    let awesome_class = class![C.w_4, C.h_4, C.inline, C.mr_4];
    if cmd.complete {
        font_awesome(awesome_class, "check").merge_attrs(class![C.text_green_500])
    } else if cmd.cancelled {
        font_awesome(awesome_class, "ban").merge_attrs(class![C.text_gray_500])
    } else if cmd.errored {
        font_awesome(awesome_class, "bell").merge_attrs(class![C.text_red_500])
    } else {
        font_awesome(awesome_class, "spinner").merge_attrs(class![C.text_gray_500, C.pulse])
    }
}

fn job_status_icon<T>(job: &RichJob) -> Node<T> {
    let awesome_style = class![C.fill_current, C.w_4, C.h_4, C.inline];
    if job.cancelled {
        font_awesome(awesome_style, "ban").merge_attrs(class![C.text_red_500])
    } else if job.errored {
        font_awesome(awesome_style, "exclamation").merge_attrs(class![C.text_red_500])
    } else if job.state == "complete" {
        font_awesome(awesome_style, "check").merge_attrs(class![C.text_green_500])
    } else {
        font_awesome(awesome_style, "spinner").merge_attrs(class![C.text_gray_500, C.pulse])
    }
}

fn step_status_icon<T>(step: &RichStep, is_open: bool) -> Node<T> {
    let awesome_style = class![C.fill_current, C.w_4, C.h_4, C.inline];
    let color = match step.state.as_ref() {
        "incomplete" => class![C.text_gray_500],
        "failed" => class![C.text_red_500],
        "success" => class![C.text_green_500],
        _ => class![C.text_gray_100],
    };
    if is_open {
        font_awesome(awesome_style, "minus-circle").merge_attrs(color)
    } else {
        font_awesome(awesome_style, "plus-circle").merge_attrs(color)
    }
}

fn close_button() -> Node<Msg> {
    button![
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

async fn fetch_the_batch<T, F, U>(ids: Vec<u32>, data_to_msg: F) -> Result<U, U>
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
        .fetch_json_data(data_to_msg)
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

fn is_finished(cmd: &RichCommand) -> bool {
    cmd.complete
}

fn is_all_finished(cmds: &[Arc<RichCommand>]) -> bool {
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

fn are_steps_consistent(model: &Model, jobs: &[Step]) -> bool {
    let check = |jid: u32| {
        if let Some(job) = model.jobs.iter().find(|job| job.id == jid) {
            let job_step_ids = extract_ids::<Step>(&job.steps);
            let step_ids = jobs.iter().map(|j| j.id).collect::<Vec<u32>>();
            // the order are guaranteed to be the same are_jobs_consistent
            job_step_ids == step_ids
        } else {
            false
        }
    };
    // the consistency on the upper levels are checked in
    match model.opens {
        Opens::None => true,
        Opens::Command(_) => true,
        Opens::CommandJob(_, jid) => check(jid),
        Opens::CommandJobSteps(_, jid, _) => check(jid),
    }
}

fn is_typed_id_in_opens(opens: &Opens, typed_id: TypedId) -> bool {
    match typed_id {
        TypedId::Command(cmd_id) => match opens {
            Opens::None => false,
            Opens::Command(cid) => cmd_id == *cid,
            Opens::CommandJob(cid, _) => cmd_id == *cid,
            Opens::CommandJobSteps(cid, _, _) => cmd_id == *cid,
        },
        TypedId::Job(job_id) => match opens {
            Opens::None => false,
            Opens::Command(_) => false,
            Opens::CommandJob(_, jid) => job_id == *jid,
            Opens::CommandJobSteps(_, jid, _) => job_id == *jid,
        },
        TypedId::Step(step_id) => match opens {
            Opens::None => false,
            Opens::Command(_) => false,
            Opens::CommandJob(_, _) => false,
            Opens::CommandJobSteps(_, _, sids) => sids.contains(&step_id),
        },
    }
}

fn interpret_click(old_opens: &Opens, the_id: TypedId) -> (Opens, bool, Option<u8>) {
    // commands behave like radio-button with the
    // jobs behave like radio button
    // steps are set of independent checkboxes
    let clear_level = match (old_opens, the_id) {
        // clear more
        (Opens::Command(c1), TypedId::Command(c2)) if *c1 != c2 => Some(2),
        (Opens::CommandJob(c1, _), TypedId::Command(c2)) if *c1 != c2 => Some(2),
        (Opens::CommandJobSteps(c1, _, _), TypedId::Command(c2)) if *c1 != c2 => Some(2),
        // clear less than ^^^
        (Opens::CommandJob(_, j1), TypedId::Job(j2)) if *j1 != j2 => Some(1),
        (Opens::CommandJobSteps(_, j1, _), TypedId::Job(j2)) if *j1 != j2 => Some(1),
        // clear nothing
        _ => None,
    };
    if is_typed_id_in_opens(old_opens, the_id) {
        (perform_close_click(old_opens, the_id), false, clear_level)
    } else {
        (perform_open_click(old_opens, the_id), true, clear_level)
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
                    Opens::Command(*cmd_id_0)
                } else {
                    cur_opens.clone()
                }
            }
            Opens::CommandJobSteps(cmd_id_0, job_id_0, _) => {
                if job_id == *job_id_0 {
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
                let step_ids = step_ids_0.iter().copied().filter(|sid| *sid != step_id).collect();
                Opens::CommandJobSteps(*cmd_id_0, *job_id_0, step_ids)
            }
        },
    }
}

fn extract_children_from_cmd(cmd: &Command) -> (u32, Vec<u32>) {
    (
        cmd.id,
        cmd.jobs.iter().filter_map(|s| extract_uri_id::<Job0>(s)).collect(),
    )
}

fn extract_children_from_job(job: &Job0) -> (u32, Vec<u32>) {
    (
        job.id,
        job.steps.iter().filter_map(|s| extract_uri_id::<Step>(s)).collect(),
    )
}

fn extract_children_from_step(step: &Step) -> (u32, Vec<u32>) {
    (step.id, Vec::new()) // steps have no descendants
}

fn extract_wait_fors_from_job(job: &Job0) -> (u32, Vec<u32>) {
    // interdependencies between jobs
    (
        job.id,
        job.wait_for.iter().filter_map(|s| extract_uri_id::<Job0>(s)).collect(),
    )
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dependency_tree::build_direct_dag;

    #[derive(Debug, Clone)]
    struct A {
        id: u32,
        deps: Vec<u32>,
        description: String,
    }

    impl A {
        fn new(id: u32, deps: &[u32], desc: &str) -> Self {
            Self {
                id,
                deps: deps.to_vec(),
                description: desc.to_string(),
            }
        }
    }

    impl Deps<u32> for A {
        fn id(&self) -> u32 {
            self.id
        }
        fn deps(&self) -> &[u32] {
            &self.deps
        }
        fn has(&self, k: &u32) -> bool {
            self.deps.contains(k)
        }
    }

    #[derive(Debug, Clone)]
    struct B {
        id: u32,
        deps: Vec<u32>,
        description: String,
    }

    impl B {
        fn new(id: u32, deps: &[u32], desc: &str) -> Self {
            Self {
                id,
                deps: deps.to_vec(),
                description: desc.to_string(),
            }
        }
    }

    impl Deps<u32> for B {
        fn id(&self) -> u32 {
            self.id
        }
        fn deps(&self) -> &[u32] {
            &self.deps
        }
        fn has(&self, k: &u32) -> bool {
            self.deps.contains(k)
        }
    }

    #[derive(Debug, Clone)]
    struct C {
        id: u32,
        deps: Vec<u32>,
        description: String,
    }

    impl C {
        fn new(id: u32, deps: &[u32], desc: &str) -> Self {
            Self {
                id,
                deps: deps.to_vec(),
                description: desc.to_string(),
            }
        }
    }

    impl Deps<u32> for C {
        fn id(&self) -> u32 {
            self.id
        }
        fn deps(&self) -> &[u32] {
            &self.deps
        }
        fn has(&self, k: &u32) -> bool {
            self.deps.contains(k)
        }
    }

    #[derive(Debug, Default, Clone)]
    struct Db {
        all_a: Vec<A>,
        all_b: Vec<B>,
        all_c: Vec<C>,
    }

    impl Db {
        fn select_a(&self, is: &[u32]) -> Vec<A> {
            self.all_a
                .iter()
                .filter(|a| is.contains(&a.id()))
                .map(|a| a.clone())
                .collect::<Vec<A>>()
        }
        fn select_b(&self, is: &[u32]) -> Vec<B> {
            self.all_b
                .iter()
                .filter(|b| is.contains(&b.id()))
                .map(|b| b.clone())
                .collect::<Vec<B>>()
        }
        fn select_c(&self, is: &[u32]) -> Vec<C> {
            self.all_c
                .iter()
                .filter(|c| is.contains(&c.id()))
                .map(|c| c.clone())
                .collect::<Vec<C>>()
        }
    }

    #[test]
    fn parse_job() {
        assert_eq!(extract_uri_id::<Job0>("/api/job/39/"), Some(39));
        assert_eq!(extract_uri_id::<Step>("/api/step/123/"), Some(123));
        assert_eq!(extract_uri_id::<Command>("/api/command/12/"), Some(12));
        assert_eq!(extract_uri_id::<Command>("/api/xxx/1/"), None);
    }

    #[test]
    fn build_dependency_view() {
        let jobs = vec![
            make_dependent_job(1, &[2, 3], "One"),
            make_dependent_job(2, &[], "Two"),
            make_dependent_job(3, &[], "Three"),
        ];
        let rich_jobs = jobs.into_iter().map(|j| RichJob::new(j, extract_wait_fors_from_job));
        let arc_jobs: Vec<Arc<RichJob>> = rich_jobs.map(|j| Arc::new(j)).collect();

        let dag = build_direct_dag(&arc_jobs);
        let dom = job_dag_view(&dag, &job_item_view);
        let awesome_style = class![C.fill_current, C.w_4, C.h_4, C.inline, C.text_green_500];
        let icon = font_awesome(awesome_style, "check");
        let expected_dom: Node<Msg> = div![div![
            // class![ C.ml_3, C.mt_1 ],
            a![
                span![class![C.mr_1], icon.clone()],
                span![class![C.cursor_pointer, C.underline], "One"],
                simple_ev(Ev::Click, Msg::Click(TypedId::Job(1))),
            ],
            div![
                class![C.ml_3, C.mt_1],
                a![
                    span![class![C.mr_1], icon.clone()],
                    span![class![C.cursor_pointer, C.underline], "Two"],
                    simple_ev(Ev::Click, Msg::Click(TypedId::Job(2))),
                ],
            ],
            div![
                class![C.ml_3, C.mt_1],
                a![
                    span![class![C.mr_1], icon.clone()],
                    span![class![C.cursor_pointer, C.underline], "Three"],
                    simple_ev(Ev::Click, Msg::Click(TypedId::Job(3))),
                ]
            ],
        ]];
        // FIXME It seems there is no any other way, https://github.com/seed-rs/seed/issues/414
        assert_eq!(format!("{:#?}", dom), format!("{:#?}", expected_dom));
    }

    #[test]
    fn interpret_click_test() {
        let start = Opens::None;

        // click on Command(12)
        let triple = interpret_click(&start, TypedId::Command(12));
        assert_eq!(&triple, &(Opens::Command(12), true, None));

        // click on Job(40)
        let triple = interpret_click(&triple.0, TypedId::Job(40));
        assert_eq!(&triple, &(Opens::CommandJob(12, 40), true, None));

        // click on Step(63)
        let triple = interpret_click(&triple.0, TypedId::Step(63));
        assert_eq!(&triple, &(Opens::CommandJobSteps(12, 40, vec![63]), true, None));

        // click on Step(62)
        let triple = interpret_click(&triple.0, TypedId::Step(62));
        assert_eq!(&triple, &(Opens::CommandJobSteps(12, 40, vec![63, 62]), true, None));

        // click on the different command, Command(54)
        let triple = interpret_click(&triple.0, TypedId::Command(54));
        assert_eq!(&triple, &(Opens::Command(54), true, Some(2)));

        // click on the Job(91)
        let triple = interpret_click(&triple.0, TypedId::Job(91));
        assert_eq!(&triple, &(Opens::CommandJob(54, 91), true, None));

        // click on the different command, Command(12)
        let triple = interpret_click(&triple.0, TypedId::Command(12));
        assert_eq!(&triple, &(Opens::Command(12), true, Some(2)));
    }

    #[test]
    fn test_async_handlers_consistency() {
        fn extract_ids<T: Deps<u32>>(ts: &[Arc<T>]) -> Vec<u32> {
            ts.iter().map(|t| t.id()).collect()
        }
        // all the packets come in random order, the model should be always consistent
        // 1 -> [10, 11] -> [20, 21, 22, 23]
        let db = build_db();
        let mut model = Model::default();
        let (a, b, c) = prepare_abc(&db, 1);
        model.assign_a(&db.select_a(&vec![1, 2]));
        model.assign_b(&db.select_b(&vec![10, 12, 13, 14]));
        model.assign_c(&db.select_c(&vec![20, 23, 14]));
        model.assign_a(&db.select_a(&vec![1, 2, 3, 4]));

        model.select = Select::SelectA(1);
        model.assign_c(&c);
        model.assign_b(&b);
        model.assign_a(&a);
        assert_eq!(extract_ids(&model.aa_view), [1, 2, 3, 4] as [u32; 4]);
        assert_eq!(extract_ids(&model.bb_view), [] as [u32; 0]);
        assert_eq!(extract_ids(&model.cc_view), [] as [u32; 0]);

        model.select = Select::SelectB(1, 11);
        model.assign_c(&c);
        model.assign_a(&a);
        model.assign_b(&b);
        assert_eq!(extract_ids(&model.aa_view), [1, 2, 3, 4] as [u32; 4]);
        assert_eq!(extract_ids(&model.bb_view), [10, 11] as [u32; 2]);
        assert_eq!(extract_ids(&model.cc_view), [] as [u32; 0]);

        model.select = Select::SelectC(1, 11, 26);
        model.assign_b(&b);
        model.assign_c(&c);
        model.assign_a(&a);
        assert_eq!(extract_ids(&model.aa_view), [1, 2, 3, 4] as [u32; 4]);
        assert_eq!(extract_ids(&model.bb_view), [10, 11] as [u32; 2]);
        assert_eq!(extract_ids(&model.cc_view), [20, 21, 26] as [u32; 3]);
    }

    fn make_dependent_job(id: u32, deps: &[u32], descr: &str) -> Job0 {
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

    fn build_db() -> Db {
        let all_a = vec![
            A::new(1, &[10, 11], "One"),
            A::new(2, &[12, 13], "Two"),
            A::new(3, &[14, 15], "Three"),
            A::new(4, &[16, 17], "Four"),
        ];
        let all_b = vec![
            B::new(10, &[20, 21], "Ten"),
            B::new(11, &[21, 26], "Eleven"),
            B::new(12, &[22, 23], "Twelve"),
            B::new(13, &[23, 28], "Thirteen"),
            B::new(14, &[24, 15], "Ten"),
            B::new(15, &[25, 20], "Eleven"),
            B::new(16, &[26, 27], "Twelve"),
            B::new(17, &[27, 22], "Thirteen"),
        ];
        let all_c = vec![
            C::new(20, &[], "Twenty and zero"),
            C::new(21, &[], "Twenty and one"),
            C::new(22, &[], "Twenty and two"),
            C::new(23, &[], "Twenty and three"),
            C::new(24, &[], "Twenty and four"),
            C::new(25, &[], "Twenty and five"),
            C::new(26, &[], "Twenty and six"),
            C::new(27, &[], "Twenty and seven"),
            C::new(28, &[], "Twenty and eight"),
            C::new(29, &[], "Twenty and nine"),
        ];
        Db { all_a, all_b, all_c }
    }

    fn prepare_abc(db: &Db, id: u32) -> (Vec<A>, Vec<B>, Vec<C>) {
        let ai = db.select_a(&vec![id]);
        let aix = ai.iter().map(|a| a.deps()).flatten().map(|a| *a).collect::<Vec<u32>>();
        let bi = db.select_b(&aix);
        let bix = bi.iter().map(|b| b.deps()).flatten().map(|b| *b).collect::<Vec<u32>>();
        let ci = db.select_c(&bix);
        let ai = db.all_a.clone(); // use all roots
        (ai, bi, ci)
    }

    #[derive(Debug, Default, Clone)]
    struct Model {
        aa: Vec<Arc<A>>,
        bb: Vec<Arc<B>>,
        cc: Vec<Arc<C>>,

        aa_view: Vec<Arc<A>>,
        bb_view: Vec<Arc<B>>,
        cc_view: Vec<Arc<C>>,

        select: Select,
    }

    #[derive(Debug, Clone)]
    enum Select {
        None,
        SelectA(u32),
        SelectB(u32, u32),
        SelectC(u32, u32, u32),
    }
    impl Default for Select {
        fn default() -> Self {
            Self::None
        }
    }

    impl Model {
        fn assign_a(&mut self, aa: &[A]) {
            let mut aas = aa.to_vec();
            aas.sort_by_key(|a| a.id());
            self.aa = aas.into_iter().map(|a| Arc::new(a.clone())).collect();
            let (consistent, _, _) = self.consistency_level(&self.select);
            if consistent {
                self.aa_view = self.aa.clone();
            }
        }
        fn assign_b(&mut self, bb: &[B]) {
            let mut bbs = bb.to_vec();
            bbs.sort_by_key(|b| b.id());
            self.bb = bbs.into_iter().map(|b| Arc::new(b.clone())).collect();
            let (_, consistent, _) = self.consistency_level(&self.select);
            if consistent {
                self.bb_view = self.bb.clone();
            }
        }

        fn assign_c(&mut self, cc: &[C]) {
            let mut ccs = cc.to_vec();
            ccs.sort_by_key(|c| c.id());
            self.cc = ccs.into_iter().map(|c| Arc::new(c.clone())).collect();
            let (_, _, consistent) = self.consistency_level(&self.select);
            if consistent {
                self.cc_view = self.cc.clone();
            }
        }

        fn consistency_level(&self, select: &Select) -> (bool, bool, bool) {
            let mut ls = [false; 3];
            match *select {
                Select::None => {}
                Select::SelectA(i) => {
                    let ao = self.aa.iter().find(|a| a.id() == i);
                    match ao {
                        Some(_) => {
                            ls[0] = true;
                        }
                        _ => {
                            ls[0] = false;
                        }
                    }
                }
                Select::SelectB(i, j) => {
                    let ao = self.aa.iter().find(|a| a.id() == i);
                    let bo = self.bb.iter().find(|b| b.id() == j);
                    match (ao, bo) {
                        (Some(a), Some(_)) => {
                            ls[0] = true;
                            ls[1] = a.deps().contains(&j);
                        }
                        (Some(_), _) => {
                            ls[0] = true;
                            ls[1] = false;
                        }
                        (_, _) => {
                            ls[0] = false;
                            ls[0] = false;
                        }
                    }
                }
                Select::SelectC(i, j, k) => {
                    let ao = self.aa.iter().find(|a| a.id() == i);
                    let bo = self.bb.iter().find(|b| b.id() == j);
                    let co = self.cc.iter().find(|c| c.id() == k);
                    match (ao, bo, co) {
                        (Some(a), Some(b), Some(_)) => {
                            ls[0] = true;
                            ls[1] = a.deps().contains(&j);
                            ls[2] = b.deps().contains(&k);
                        }
                        (Some(a), Some(_), _) => {
                            ls[0] = true;
                            ls[1] = a.deps().contains(&j);
                            ls[2] = false;
                        }
                        (Some(_), _, _) => {
                            ls[0] = true;
                            ls[1] = false;
                            ls[2] = false;
                        }
                        (_, _, _) => {
                            ls[0] = false;
                            ls[1] = false;
                            ls[2] = false;
                        }
                    }
                }
            }
            (ls[0], ls[1], ls[2])
        }
    }
}
