// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{font_awesome::*, modal},
    dependency_tree::{build_direct_dag, traverse_graph, DependencyDAG, Deps, Rich},
    extensions::{MergeAttrs as _, NodeExt as _, RequestExt as _},
    generated::css_classes::C,
    key_codes, sleep_with_handle, GMsg,
};
use futures::channel::oneshot;
use iml_wire_types::{ApiList, AvailableTransition, Command, EndpointName, Job, Step};
use regex::{Captures, Regex};
use seed::{prelude::*, *};
use serde::de::DeserializeOwned;
use std::{
    collections::{HashMap, HashSet},
    fmt::{self, Display},
    sync::Arc,
    time::Duration,
};

/// The component polls `/api/(command|job|step)/` endpoint and this constant defines how often it
/// does.
const POLL_INTERVAL: Duration = Duration::from_millis(1000);

type Job0 = Job<Option<serde_json::Value>>;

type RichCommand = Rich<i32, Arc<Command>>;
type RichJob = Rich<i32, Arc<Job0>>;
type RichStep = Rich<i32, Arc<Step>>;

type JobsGraph = DependencyDAG<i32, RichJob>;

#[derive(Copy, Clone, Hash, PartialEq, Eq, Ord, PartialOrd, Debug)]
pub struct CmdId(i32);

#[derive(Copy, Clone, Hash, PartialEq, Eq, Ord, PartialOrd, Debug)]
pub struct JobId(i32);

#[derive(Copy, Clone, Hash, PartialEq, Eq, Debug)]
pub enum TypedId {
    Cmd(i32),
    Job(i32),
    Step(i32),
}

#[derive(Clone, Debug)]
struct TransitionState(String);

#[derive(Clone, Eq, PartialEq, Debug, Default)]
pub struct Select(HashSet<TypedId>);

impl Display for Select {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{:?}", self)
    }
}

impl Select {
    fn split(&self) -> (Vec<i32>, Vec<i32>, Vec<i32>) {
        fn insert_in_sorted(ids: &mut Vec<i32>, id: i32) {
            match ids.binary_search(&id) {
                Ok(_) => {}
                Err(pos) => ids.insert(pos, id),
            }
        }
        let mut cmd_ids = Vec::new();
        let mut job_ids = Vec::new();
        let mut step_ids = Vec::new();
        for t in &self.0 {
            match t {
                TypedId::Cmd(c) => insert_in_sorted(&mut cmd_ids, *c),
                TypedId::Job(j) => insert_in_sorted(&mut job_ids, *j),
                TypedId::Step(s) => insert_in_sorted(&mut step_ids, *s),
            }
        }
        (cmd_ids, job_ids, step_ids)
    }

    fn contains(&self, id: TypedId) -> bool {
        self.0.contains(&id)
    }

    fn perform_click(&mut self, id: TypedId) -> bool {
        if self.0.contains(&id) {
            !self.0.remove(&id)
        } else {
            self.0.insert(id)
        }
    }
}

#[derive(Clone, Debug)]
pub struct Context<'a> {
    pub steps_view: &'a HashMap<JobId, Vec<Arc<RichStep>>>,
    pub select: &'a Select,
    pub cancelling_jobs: &'a HashSet<i32>,
}

#[derive(Clone, Debug)]
pub enum Input {
    Commands(Vec<Arc<Command>>),
    Ids(Vec<i32>),
}

#[derive(Default, Debug)]
pub struct Model {
    pub tree_cancel: Option<oneshot::Sender<()>>,

    pub commands: HashMap<i32, Arc<RichCommand>>,
    pub commands_view: Vec<Arc<RichCommand>>,

    pub jobs: HashMap<i32, Arc<RichJob>>,
    pub jobs_graphs: HashMap<CmdId, JobsGraph>,

    pub steps: HashMap<i32, Arc<RichStep>>,
    pub steps_view: HashMap<JobId, Vec<Arc<RichStep>>>,

    pub select: Select,
    pub cancelling_jobs: HashSet<i32>,
    pub modal: modal::Model,
}

#[derive(Clone, Debug)]
pub enum Msg {
    Modal(modal::Msg),
    FireCommands(Input),
    FetchTree,
    FetchedCommands(Box<fetch::ResponseDataResult<ApiList<Command>>>),
    FetchedJobs(Box<fetch::ResponseDataResult<ApiList<Job0>>>),
    FetchedSteps(Box<fetch::ResponseDataResult<ApiList<Step>>>),
    Click(TypedId),
    CancelJob(i32),
    CancelledJob(i32, Box<fetch::ResponseDataResult<Job0>>),
    Noop,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match msg {
        Msg::Modal(msg) => {
            if msg == modal::Msg::Close {
                model.clear();
            }
            modal::update(msg, &mut model.modal, &mut orders.proxy(Msg::Modal));
        }
        Msg::FireCommands(cmds) => {
            model.select = Select(HashSet::new());
            model.modal.open = true;

            match cmds {
                Input::Commands(cmds) => {
                    if let Some(cmd) = cmds.first() {
                        model.select.perform_click(TypedId::Cmd(cmd.id));
                    }
                    // use the (little) optimization:
                    // if we already have the commands and they all finished, we don't need to poll them anymore
                    model.update_commands(cmds);
                    if !is_all_commands_finished(&model.commands) {
                        orders.send_msg(Msg::FetchTree);
                    }
                }
                Input::Ids(ids) => {
                    // we have ids only, so we need to populate the vector first
                    orders.perform_cmd(fetch_the_batch(ids, |x| Msg::FetchedCommands(Box::new(x))));
                }
            }
        }
        Msg::FetchTree => {
            model.tree_cancel = None;
            if !is_all_commands_finished(&model.commands) {
                schedule_fetch_tree(model, orders);
            }
        }
        Msg::FetchedCommands(commands_data_result) => {
            match *commands_data_result {
                Ok(api_list) => {
                    model.update_commands(api_list.objects.into_iter().map(Arc::new).collect());
                }
                Err(e) => {
                    error!(format!("Failed to fetch commands {:#?}", e));
                    orders.skip();
                }
            }
            if !is_all_commands_finished(&model.commands) {
                let (cancel, fut) = sleep_with_handle(POLL_INTERVAL, Msg::FetchTree, Msg::Noop);
                model.tree_cancel = Some(cancel);
                orders.perform_cmd(fut);
            }
        }
        Msg::FetchedJobs(jobs_data_result) => match *jobs_data_result {
            Ok(api_list) => {
                model.update_jobs(api_list.objects.into_iter().map(Arc::new).collect());
            }
            Err(e) => {
                error!(format!("Failed to fetch jobs {:#?}", e));
                orders.skip();
            }
        },
        Msg::FetchedSteps(steps_data_result) => match *steps_data_result {
            Ok(api_list) => {
                model.update_steps(api_list.objects.into_iter().map(Arc::new).collect());
            }
            Err(e) => {
                error!(format!("Failed to fetch steps {:#?}", e));
                orders.skip();
            }
        },
        Msg::Click(the_id) => {
            let do_fetch = model.select.perform_click(the_id);
            if do_fetch {
                schedule_fetch_tree(model, orders);
            }
        }
        Msg::CancelJob(job_id) => {
            if let Some(job) = model.jobs.get(&job_id) {
                if let Some(ct) = find_cancel_transition(job) {
                    if model.cancelling_jobs.insert(job_id) {
                        let fut = apply_job_transition(job_id, TransitionState(ct.state.clone()));
                        orders.skip().perform_cmd(fut);
                    }
                }
            }
        }
        Msg::CancelledJob(job_id, job_result) => {
            model.cancelling_jobs.remove(&job_id);
            if let Err(e) = *job_result {
                error!(format!("Failed to cancel job {}: {:#?}", job_id, e));
                orders.skip();
            }
        }
        Msg::Noop => {}
    }
}

fn schedule_fetch_tree(model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    let (cmd_ids, job_ids, _) = &model.select.split();
    // grab all the dependencies for the chosen items, except those that already loaded and completed
    let load_cmd_ids = extract_sorted_keys(&model.commands)
        .into_iter()
        .filter(|c| to_load_cmd(model, *c))
        .collect::<Vec<i32>>();
    let load_job_ids = cmd_ids
        .iter()
        .filter(|c| model.commands.contains_key(c))
        .flat_map(|c| model.commands[c].deps())
        .filter(|j| to_load_job(model, **j))
        .copied()
        .collect::<Vec<i32>>();
    let load_step_ids = job_ids
        .iter()
        .filter(|j| model.jobs.contains_key(j))
        .flat_map(|j| model.jobs[j].deps())
        .filter(|s| to_load_step(model, **s))
        .copied()
        .collect::<Vec<i32>>();

    orders.skip();
    if !load_cmd_ids.is_empty() {
        orders.perform_cmd(fetch_the_batch(load_cmd_ids, |x| Msg::FetchedCommands(Box::new(x))));
    }
    if !load_job_ids.is_empty() {
        orders.perform_cmd(fetch_the_batch(load_job_ids, |x| Msg::FetchedJobs(Box::new(x))));
    }
    if !load_step_ids.is_empty() {
        orders.perform_cmd(fetch_the_batch(load_step_ids, |x| Msg::FetchedSteps(Box::new(x))));
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
                if model.commands_view.is_empty() {
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
                            model.commands_view.iter().map(|x| { command_item_view(model, x) })
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
    let is_open = model.select.contains(TypedId::Cmd(x.id));
    // all commands will be marked complete when they finished, it's the absence of other states that makes them successful
    let border = if !is_open {
        C.border_transparent
    } else if x.errored {
        C.border_red_500
    } else if x.cancelled {
        C.border_gray_500
    } else if x.complete {
        C.border_green_500
    } else {
        C.border_transparent
    };

    let open_icon = if is_open {
        "chevron-circle-up"
    } else {
        "chevron-circle-down"
    };
    let job_tree = job_tree_view(model, CmdId(x.id));
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
                simple_ev(Ev::Click, Msg::Click(TypedId::Cmd(x.id))),
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
            ]
        ]
    ]
}

pub fn job_tree_view(model: &Model, parent_cid: CmdId) -> Node<Msg> {
    if !model.jobs_graphs.contains_key(&parent_cid) || model.jobs_graphs[&parent_cid].is_empty() {
        div![
            class![C.my_8, C.text_center, C.text_gray_500],
            font_awesome(class![C.w_8, C.h_8, C.inline, C.pulse], "spinner"),
        ]
    } else {
        let mut ctx = Context {
            steps_view: &model.steps_view,
            select: &model.select,
            cancelling_jobs: &model.cancelling_jobs,
        };
        let dag_nodes = traverse_graph(
            &model.jobs_graphs[&parent_cid],
            &job_item_view,
            &job_item_combine,
            &mut ctx,
        );
        div![
            class![C.font_ordinary, C.text_gray_700],
            h4![class![C.text_lg, C.font_medium], "Jobs"],
            div![class![C.p_1, C.pb_2, C.mb_1, C.overflow_auto], div![dag_nodes]],
        ]
    }
}

fn job_item_view(job: Arc<RichJob>, is_new: bool, ctx: &mut Context) -> Node<Msg> {
    let icon = job_status_icon(job.as_ref());
    if !is_new {
        empty![]
    } else if job.steps.is_empty() {
        span![span![class![C.mr_1], icon], span![job.description]]
    } else {
        let cancelling = ctx.cancelling_jobs.contains(&job.id);
        let cancel_btn = job_item_cancel_button(&job, cancelling);
        let is_open = ctx.select.contains(TypedId::Job(job.id));
        let def_vec = Vec::new();
        let steps = ctx.steps_view.get(&JobId(job.id)).unwrap_or(&def_vec);
        div![
            a![
                span![class![C.mr_1], icon],
                span![class![C.cursor_pointer, C.underline], job.description],
                simple_ev(Ev::Click, Msg::Click(TypedId::Job(job.id))),
            ],
            cancel_btn,
            step_list_view(steps, ctx.select, is_open),
        ]
    }
}

fn job_item_combine(parent: Node<Msg>, acc: Vec<Node<Msg>>, _ctx: &mut Context) -> Node<Msg> {
    if !parent.is_empty() {
        // all the dependencies are shifted with the indent
        let acc_plus = acc.into_iter().map(|a| a.merge_attrs(class![C.ml_3, C.mt_1]));
        div![parent, acc_plus]
    } else {
        empty![]
    }
}

fn job_item_cancel_button(job: &Arc<RichJob>, cancelling: bool) -> Node<Msg> {
    if let Some(trans) = find_cancel_transition(job) {
        let cancel_btn: Node<Msg> = div![
            class![C.inline, C.ml_1, C.px_1, C.rounded_lg, C.text_white, C.cursor_pointer],
            trans.label,
        ];
        if !cancelling {
            cancel_btn
                .merge_attrs(class![C.bg_blue_500, C.hover__bg_blue_400])
                .with_listener(simple_ev(Ev::Click, Msg::CancelJob(job.id)))
        } else {
            // ongoing action will render gray button without the handler
            cancel_btn.merge_attrs(class![C.bg_gray_500, C.hover__bg_gray_400])
        }
    } else {
        empty![]
    }
}

fn step_list_view(steps: &[Arc<RichStep>], select: &Select, is_open: bool) -> Node<Msg> {
    if !is_open {
        empty![]
    } else if steps.is_empty() {
        div![
            class![C.my_8, C.text_center, C.text_gray_500],
            font_awesome(class![C.w_8, C.h_8, C.inline, C.pulse], "spinner"),
        ]
    } else {
        div![ul![
            class![C.p_1, C.pb_2, C.mb_1, C.overflow_auto],
            steps.iter().map(|x| {
                let is_open = select.contains(TypedId::Step(x.id));
                li![step_item_view(x, is_open)]
            })
        ]]
    }
}

fn step_item_view(step: &RichStep, is_open: bool) -> Vec<Node<Msg>> {
    let icon = step_status_icon(step);
    let item_caption = div![
        class![C.flex],
        div![
            attrs![At::Style => "flex: 0 0 1em"],
            class![C.mx_2, C.cursor_pointer],
            icon,
            simple_ev(Ev::Click, Msg::Click(TypedId::Step(step.id))),
        ],
        div![
            class![C.flex_grow, C.cursor_pointer, C.underline],
            step.class_name,
            simple_ev(Ev::Click, Msg::Click(TypedId::Step(step.id))),
        ],
    ];
    let item_body = if !is_open {
        empty![]
    } else {
        // note, we cannot just use the Debug instance for step.args,
        // because the keys traversal order changes every time the HashMap is created
        let mut arg_keys = step.args.keys().collect::<Vec<&String>>();
        arg_keys.sort();
        let mut args: Vec<Node<Msg>> = Vec::with_capacity(step.args.len());
        for k in arg_keys {
            args.push(span![class![C.text_blue_300], &format!("{}: ", k)]);
            args.push(plain![format!(
                "{}\n",
                step.args.get(k).unwrap_or(&serde_json::value::Value::Null)
            )]);
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
        let caption_class = class![C.text_lg, C.font_medium];
        // show logs and backtrace if the step has failed
        let backtrace_view = if step.state == "failed" && !step.backtrace.is_empty() {
            vec![h4![&caption_class, "Backtrace"], pre![&pre_class, step.backtrace]]
        } else {
            vec![]
        };
        let log_view = if step.state == "failed" && !step.log.is_empty() {
            vec![h4![&caption_class, "Logs"], pre![&pre_class, step.log]]
        } else {
            vec![]
        };
        let console_view = if !step.console.is_empty() {
            vec![h4![&caption_class, "Console output"], pre![&pre_class, step.console]]
        } else {
            vec![]
        };
        div![
            class![C.flex],
            div![
                attrs![At::Style => "flex: 0 0 1em"],
                class![C.border_r_2, C.border_gray_300, C.hover__border_gray_600],
                simple_ev(Ev::Click, Msg::Click(TypedId::Step(step.id))),
            ],
            div![attrs![At::Style => "flex: 0 0 1em"]],
            div![
                class![C.float_right, C.flex_grow],
                h4![&caption_class, "Arguments"],
                pre![&pre_class, args],
                backtrace_view,
                log_view,
                console_view,
            ]
        ]
    };
    vec![item_caption, item_body]
}

fn status_text(cmd: &RichCommand) -> &'static str {
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

fn cmd_status_icon<T>(cmd: &RichCommand) -> Node<T> {
    let awesome_class = class![C.w_4, C.h_4, C.inline, C.mr_4];
    if cmd.cancelled {
        font_awesome(awesome_class, "ban").merge_attrs(class![C.text_gray_500])
    } else if cmd.errored {
        font_awesome(awesome_class, "bell").merge_attrs(class![C.text_red_500])
    } else if cmd.complete {
        font_awesome(awesome_class, "check").merge_attrs(class![C.text_green_500])
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

fn step_status_icon<T>(step: &RichStep) -> Node<T> {
    let awesome_style = class![C.fill_current, C.w_4, C.h_4, C.inline];
    match &step.state[..] {
        "cancelled" => font_awesome(awesome_style, "ban").merge_attrs(class![C.text_red_500]),
        "failed" => font_awesome(awesome_style, "exclamation").merge_attrs(class![C.text_red_500]),
        "success" => font_awesome(awesome_style, "check").merge_attrs(class![C.text_green_500]),
        _ /* "incomplete" */ => font_awesome(awesome_style, "spinner").merge_attrs(class![C.text_gray_500, C.pulse]),
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

async fn fetch_the_batch<T, F, U>(ids: Vec<i32>, data_to_msg: F) -> Result<U, U>
where
    T: DeserializeOwned + EndpointName + 'static,
    F: FnOnce(ResponseDataResult<ApiList<T>>) -> U,
    U: 'static,
{
    // e.g. GET /api/something/?id__in=1&id__in=2&id__in=11&limit=0
    let mut ids: Vec<_> = ids.into_iter().map(|x| ("id__in", x)).collect();
    ids.push(("limit", 0));
    match Request::api_query(T::endpoint_name(), &ids) {
        Ok(req) => req.fetch_json_data(data_to_msg).await,
        Err(_) => {
            // we always can url encode a vector of i32-s
            unreachable!("Cannot encode request for {} with params {:?}", T::endpoint_name(), ids)
        }
    }
}

async fn apply_job_transition(job_id: i32, transition_state: TransitionState) -> Result<Msg, Msg> {
    let json = serde_json::json!({
        "id": job_id,
        "state": transition_state.0,
    });
    let req = Request::api_item(Job0::endpoint_name(), job_id)
        .with_auth()
        .method(fetch::Method::Put)
        .send_json(&json);
    req.fetch_json_data(|x| Msg::CancelledJob(job_id, Box::new(x))).await
}

fn extract_uri_id<T: EndpointName>(input: &str) -> Option<i32> {
    lazy_static::lazy_static! {
        static ref RE: Regex = Regex::new(r"/api/(\w+)/(\d+)/").unwrap();
    }
    RE.captures(input).and_then(|cap: Captures| {
        let s = cap.get(1).unwrap().as_str();
        let t = cap.get(2).unwrap().as_str();
        if s == T::endpoint_name() {
            t.parse::<i32>().ok()
        } else {
            None
        }
    })
}

fn to_load_cmd(model: &Model, cmd_id: i32) -> bool {
    // load the command if it is not found or is not complete
    model.commands.get(&cmd_id).map(|c| !c.complete).unwrap_or(true)
}

fn to_load_job(model: &Model, job_id: i32) -> bool {
    // job.state can be "pending", "tasked" or "complete"
    // if a job is errored or cancelled, it is also complete
    model.jobs.get(&job_id).map(|j| j.state != "complete").unwrap_or(true)
}

fn to_load_step(model: &Model, step_id: i32) -> bool {
    // step.state can be "success", "failed" or "incomplete"
    model
        .steps
        .get(&step_id)
        .map(|s| s.state == "incomplete")
        .unwrap_or(true)
}

fn is_all_commands_finished(cmds: &HashMap<i32, Arc<RichCommand>>) -> bool {
    cmds.values().all(|c| c.complete)
}

fn find_cancel_transition(job: &Arc<RichJob>) -> Option<&AvailableTransition> {
    job.available_transitions.iter().find(|at| at.state == "cancelled")
}

fn extract_children_from_cmd(cmd: &Arc<Command>) -> (i32, Vec<i32>) {
    let mut deps = cmd
        .jobs
        .iter()
        .filter_map(|s| extract_uri_id::<Job0>(s))
        .collect::<Vec<i32>>();
    deps.sort();
    (cmd.id, deps)
}

fn extract_children_from_job(job: &Arc<Job0>) -> (i32, Vec<i32>) {
    let mut deps = job
        .steps
        .iter()
        .filter_map(|s| extract_uri_id::<Step>(s))
        .collect::<Vec<i32>>();
    deps.sort();
    (job.id, deps)
}

fn extract_children_from_step(step: &Arc<Step>) -> (i32, Vec<i32>) {
    (step.id, Vec::new()) // steps have no descendants
}

fn extract_wait_fors_from_job(job: &Job0, jobs: &HashMap<i32, Arc<RichJob>>) -> (i32, Vec<i32>) {
    // Extract the interdependencies between jobs.
    // See [command_modal::tests::test_jobs_ordering]
    let mut deps = job
        .wait_for
        .iter()
        .filter_map(|s| extract_uri_id::<Job0>(s))
        .collect::<Vec<i32>>();
    deps.sort_by(|i1, i2| {
        let t1 = jobs
            .get(i1)
            .map(|arj| (-(arj.deps.len() as i32), &arj.description[..], arj.id))
            .unwrap_or((0, "", *i1));
        let t2 = jobs
            .get(i2)
            .map(|arj| (-(arj.deps.len() as i32), &arj.description[..], arj.id))
            .unwrap_or((0, "", *i2));
        t1.cmp(&t2)
    });
    (job.id, deps)
}

fn extract_sorted_keys<T>(hm: &HashMap<i32, T>) -> Vec<i32> {
    let mut ids = hm.keys().copied().collect::<Vec<_>>();
    ids.sort();
    ids
}

fn convert_to_sorted_vec<T>(hm: &HashMap<i32, Arc<T>>) -> Vec<Arc<T>> {
    extract_sorted_keys(hm)
        .into_iter()
        .map(|k| Arc::clone(&hm[&k]))
        .collect()
}

fn convert_to_rich_hashmap<T>(ts: Vec<T>, extract: impl Fn(&T) -> (i32, Vec<i32>)) -> HashMap<i32, Arc<Rich<i32, T>>> {
    ts.into_iter()
        .map(|t| {
            let (id, deps) = extract(&t);
            (id, Arc::new(Rich { id, deps, inner: t }))
        })
        .collect()
}

/// NOTE: the slices must be sorted
pub fn is_subset<T: PartialEq>(part: &[T], all: &[T]) -> bool {
    let mut idx = 0;
    for it in part {
        while (idx < all.len()) && (&all[idx] != it) {
            idx += 1;
        }
        if idx == all.len() {
            return false;
        }
    }
    true
}

impl Model {
    fn clear(&mut self) {
        self.tree_cancel = None;
        self.commands.clear();
        self.commands_view.clear();
        self.jobs.clear();
        self.jobs_graphs.clear();
        self.steps.clear();
        self.steps_view.clear();
        self.select = Default::default();
        self.cancelling_jobs.clear();
    }

    fn update_commands(&mut self, cmds: Vec<Arc<Command>>) {
        let commands = convert_to_rich_hashmap(cmds, extract_children_from_cmd);
        self.commands.extend(commands);
        let tuple = self.check_back_consistency();
        self.refresh_view(tuple);
    }

    fn update_jobs(&mut self, jobs: Vec<Arc<Job0>>) {
        let jobs = convert_to_rich_hashmap(jobs, extract_children_from_job);
        self.jobs.extend(jobs);
        let tuple = self.check_back_consistency();
        self.refresh_view(tuple);
    }

    fn update_steps(&mut self, steps: Vec<Arc<Step>>) {
        let steps = convert_to_rich_hashmap(steps, extract_children_from_step);
        self.steps.extend(steps);
        let tuple = self.check_back_consistency();
        self.refresh_view(tuple);
    }

    /// We perform the consistency check of the current collections
    /// `self.commands`, `self.jobs` and `self.steps`.
    /// The selection, if it is non-empty, places additional constraints.
    fn check_back_consistency(&self) -> (bool, bool, bool) {
        let mut ok = [false; 3];

        // check between layers
        let cmd_ids = extract_sorted_keys(&self.commands);
        let job_ids = extract_sorted_keys(&self.jobs);
        let step_ids = extract_sorted_keys(&self.steps);
        ok[0] = !self.commands.is_empty();
        ok[1] = job_ids
            .iter()
            .all(|j| self.commands.values().any(|cmd| cmd.deps().contains(j)));
        ok[2] = step_ids
            .iter()
            .all(|s| self.jobs.values().any(|job| job.deps().contains(s)));

        // the additional constraints from the selection
        let (cs, js, ss) = self.select.split();
        ok[0] = ok[0] && is_subset(&cs, &cmd_ids);
        ok[1] = ok[1] && is_subset(&js, &job_ids);
        ok[2] = ok[2] && is_subset(&ss, &step_ids);

        // make ensure the consistency levels are ordered
        if ok[0] && ok[1] && ok[2] {
            (true, true, true)
        } else if ok[0] && ok[1] {
            (true, true, false)
        } else if ok[0] {
            (true, false, false)
        } else {
            (false, false, false)
        }
    }

    fn refresh_view(&mut self, layers: (bool, bool, bool)) {
        let (cmds_ok, jobs_ok, steps_ok) = layers;
        if cmds_ok {
            self.commands_view = convert_to_sorted_vec(&self.commands);
        }
        if jobs_ok {
            let mut jobs_graphs = HashMap::new();
            for (c, cmd) in &self.commands {
                if cmd.deps().iter().all(|j| self.jobs.contains_key(j)) {
                    let extract_fun = |job: &Arc<Job0>| extract_wait_fors_from_job(job, &self.jobs);
                    let jobs_graph_data = cmd
                        .deps()
                        .iter()
                        .map(|k| RichJob::new(Arc::clone(&self.jobs[k].inner), extract_fun))
                        .collect::<Vec<RichJob>>();
                    let graph = build_direct_dag(&jobs_graph_data);
                    jobs_graphs.insert(CmdId(*c), graph);
                }
            }
            self.jobs_graphs = jobs_graphs;
        }
        if steps_ok {
            let mut steps_view = HashMap::new();
            for (j, job) in &self.jobs {
                let steps = &self.steps;
                if job.deps().iter().all(|s| steps.contains_key(s)) {
                    let steps = job
                        .deps()
                        .iter()
                        .map(|s| Arc::clone(&steps[s]))
                        .collect::<Vec<Arc<RichStep>>>();
                    steps_view.insert(JobId(*j), steps);
                }
            }
            self.steps_view = steps_view;
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand_core::{RngCore, SeedableRng};
    use rand_xoshiro::Xoroshiro64Star;
    use std::fmt::Debug;
    use std::hash::Hash;
    use std::iter;

    #[derive(Default, Clone, Debug)]
    struct Db {
        all_cmds: Vec<Arc<Command>>,
        all_jobs: Vec<Arc<Job0>>,
        all_steps: Vec<Arc<Step>>,
    }

    impl Db {
        fn select_cmds(&self, is: &[i32]) -> Vec<Arc<Command>> {
            self.all_cmds
                .iter()
                .filter(|x| is.contains(&x.id))
                .map(|x| Arc::clone(x))
                .collect()
        }
        fn select_jobs(&self, is: &[i32]) -> Vec<Arc<Job0>> {
            self.all_jobs
                .iter()
                .filter(|x| is.contains(&x.id))
                .map(|x| Arc::clone(x))
                .collect()
        }
        fn select_steps(&self, is: &[i32]) -> Vec<Arc<Step>> {
            self.all_steps
                .iter()
                .filter(|x| is.contains(&x.id))
                .map(|x| Arc::clone(x))
                .collect()
        }
    }

    #[derive(Debug, Clone)]
    struct Context0 {
        level: usize,
    }

    #[test]
    fn test_parse_job() {
        assert_eq!(extract_uri_id::<Job0>("/api/job/39/"), Some(39));
        assert_eq!(extract_uri_id::<Step>("/api/step/123/"), Some(123));
        assert_eq!(extract_uri_id::<Command>("/api/command/12/"), Some(12));
        assert_eq!(extract_uri_id::<Command>("/api/xxx/1/"), None);
    }

    #[test]
    fn test_is_subset() {
        let all = vec![1, 2, 3, 4, 5];
        assert_eq!(is_subset(&vec![1, 2, 3], &all), true);
        assert_eq!(is_subset(&vec![1, 3, 5], &all), true);
        assert_eq!(is_subset(&vec![], &all), true);
        assert_eq!(is_subset(&all, &all), true);

        assert_eq!(is_subset(&vec![1, 6], &all), false);
        // if not sorted, the correctness is not guaranteed
        assert_eq!(is_subset(&vec![5, 1], &all), false);
    }

    #[test]
    fn test_selection_split() {
        let select = Select(
            vec![
                TypedId::Cmd(1),
                TypedId::Cmd(1),
                TypedId::Cmd(2),
                TypedId::Job(13),
                TypedId::Job(12),
                TypedId::Job(11),
                TypedId::Step(23),
                TypedId::Step(22),
                TypedId::Step(21),
            ]
            .into_iter()
            .collect(),
        );
        let (cs, js, ss) = select.split();
        assert_eq!(cs, vec![1, 2]);
        assert_eq!(js, vec![11, 12, 13]);
        assert_eq!(ss, vec![21, 22, 23]);
    }

    #[test]
    fn test_jobs_ordering() {
        // The jobs' dependencies (vector of i32) are sorted in special order so that the
        // jobs with more dependencies come first. If the number of dependencies are equal,
        // they are sorted by alphabetical order by the description.
        // If the description is the same, then the jobs are ordered by id.
        // The sort order of the jobs themself does NOT matter.
        let mut rng = Xoroshiro64Star::seed_from_u64(555);
        let db = build_db_2();
        let commands = db.select_cmds(&[109]);
        let mut jobs = db.select_jobs(&extract_ids::<Job0>(&commands[0].jobs));
        for i in (1..jobs.len()).rev() {
            let j = (rng.next_u64() as usize) % (i + 1);
            jobs.swap(i, j);
        }
        let mut model = Model::default();
        model.jobs = convert_to_rich_hashmap(jobs, extract_children_from_job);
        model.commands = convert_to_rich_hashmap(commands, extract_children_from_cmd);

        // here the [command_modal::extract_wait_fors_from_job] function plays
        model.refresh_view((false, true, false));

        let dag = &model.jobs_graphs[&CmdId(109)];
        let mut ctx = Context0 { level: 0 };
        let result = traverse_graph(dag, &rich_job_to_string, &rich_job_combine_strings, &mut ctx).join("");
        assert_eq!(result, WELL_ORDERED_TREE);
    }

    /// There could the the problem, when `schedule_fetch_tree` made the api requests
    /// in one order, but during delays or something the responses may come in different
    /// order. In all such cases, however, model should remain consistent,
    /// and the test checks this.
    #[test]
    fn test_async_handlers_consistency() {
        let mut rng = Xoroshiro64Star::seed_from_u64(555);
        let db = build_db_1();
        let mut model = Model::default();
        let cmd_ids = db.all_cmds.iter().map(|x| x.id).collect::<Vec<_>>();
        let selects = generate_random_selects(&db, &mut rng, 200);
        for select in selects {
            let sel_cmd_ids = if select.0.is_empty() {
                cmd_ids.clone()
            } else {
                let (cs, _, _) = select.split();
                cs
            };
            let (c, j, s) = prepare_subset(&db, &sel_cmd_ids);
            model.clear();
            model.select = select.clone();
            model.update_commands(c.clone());
            model.update_jobs(j.clone());
            model.update_steps(s.clone());
            let expected_cmd = to_str_vec(std::mem::replace(&mut model.commands_view, Vec::new()));
            let expected_jobs = to_str_hm(std::mem::replace(&mut model.jobs_graphs, HashMap::new()));
            let expected_steps = to_str_hm(std::mem::replace(&mut model.steps_view, HashMap::new()));

            let permutations = vec![[1, 3, 2], [2, 1, 3], [2, 3, 1], [3, 1, 2], [3, 2, 1]];
            for permutation in permutations {
                model.clear();
                model.select = select.clone();
                // we simulate, that FetchCommands, FetchJobs and FetchSteps come in arbitrary order
                for p in &permutation {
                    match p {
                        1 => model.update_commands(c.clone()),
                        2 => model.update_jobs(j.clone()),
                        3 => model.update_steps(s.clone()),
                        _ => unreachable!(),
                    }
                }

                let actual_cmd = to_str_vec(std::mem::replace(&mut model.commands_view, Vec::new()));
                let actual_jobs = to_str_hm(std::mem::replace(&mut model.jobs_graphs, HashMap::new()));
                let actual_steps = to_str_hm(std::mem::replace(&mut model.steps_view, HashMap::new()));
                assert_eq!(actual_cmd, expected_cmd);
                assert_eq!(actual_jobs, expected_jobs);
                assert_eq!(actual_steps, expected_steps);
            }
        }
    }

    fn to_str_vec<V: Debug>(vec: Vec<V>) -> Vec<String> {
        vec.into_iter().map(|x| format!("{:?}", x)).collect()
    }

    fn to_str_hm<K: Hash + Eq, V: Debug>(hm: HashMap<K, V>) -> HashMap<K, String> {
        hm.into_iter().map(|(k, v)| (k, format!("{:?}", v))).collect()
    }

    fn make_command(id: i32, jobs: &[i32], msg: &str) -> Arc<Command> {
        Arc::new(Command {
            cancelled: false,
            complete: false,
            created_at: "2020-03-16T07:22:34.491600".to_string(),
            errored: false,
            id,
            jobs: jobs.iter().map(|x| format!("/api/job/{}/", x)).collect(),
            logs: "".to_string(),
            message: msg.to_string(),
            resource_uri: format!("/api/command/{}/", id),
        })
    }

    fn make_job(id: i32, cmd_id: CmdId, steps: &[i32], wait_for: &[i32], descr: &str) -> Arc<Job0> {
        Arc::new(Job0 {
            available_transitions: vec![],
            cancelled: false,
            class_name: "".to_string(),
            commands: iter::once(cmd_id)
                .map(|CmdId(id)| format!("/api/command/{}/", id))
                .collect(),
            created_at: "2020-03-16T07:22:34.491600".to_string(),
            description: descr.to_string(),
            errored: false,
            id,
            modified_at: "".to_string(),
            read_locks: vec![],
            resource_uri: format!("/api/job/{}/", id),
            state: "complete".to_string(),
            step_results: Default::default(),
            steps: steps.iter().map(|x| format!("/api/step/{}/", x)).collect(),
            wait_for: wait_for.iter().map(|x| format!("/api/job/{}/", x)).collect(),
            write_locks: vec![],
        })
    }

    fn make_step(id: i32, class_name: &str) -> Arc<Step> {
        Arc::new(Step {
            args: Default::default(),
            backtrace: "".to_string(),
            class_name: class_name.to_string(),
            console: "".to_string(),
            created_at: "2020-03-16T07:22:34.491600".to_string(),
            description: "".to_string(),
            id,
            log: "".to_string(),
            modified_at: "2020-03-16T07:22:34.491600".to_string(),
            resource_uri: format!("/api/step/{}/", id),
            result: None,
            state: "incomplete".to_string(),
            step_count: 0,
            step_index: 0,
        })
    }

    fn build_db_1() -> Db {
        let all_cmds = vec![
            make_command(1, &[10, 11], "One"),
            make_command(2, &[12, 13], "Two"),
            make_command(3, &[14, 15], "Three"),
            make_command(4, &[16, 17], "Four"),
        ];
        let all_jobs = vec![
            make_job(10, CmdId(1), &[20, 21], &[11], "Ten"),
            make_job(11, CmdId(1), &[21, 26], &[], "Eleven"),
            make_job(12, CmdId(2), &[22, 23], &[13], "Twelve"),
            make_job(13, CmdId(2), &[23, 28], &[], "Thirteen"),
            make_job(14, CmdId(3), &[24, 15], &[], "Ten"),
            make_job(15, CmdId(3), &[25, 20], &[], "Eleven"),
            make_job(16, CmdId(4), &[26, 27], &[], "Twelve"),
            make_job(17, CmdId(4), &[27, 22], &[], "Thirteen"),
        ];
        let all_steps = vec![
            make_step(20, "Twenty and zero"),
            make_step(21, "Twenty and one"),
            make_step(22, "Twenty and two"),
            make_step(23, "Twenty and three"),
            make_step(24, "Twenty and four"),
            make_step(25, "Twenty and five"),
            make_step(26, "Twenty and six"),
            make_step(27, "Twenty and seven"),
            make_step(28, "Twenty and eight"),
            make_step(29, "Twenty and nine"),
        ];
        Db {
            all_cmds,
            all_jobs,
            all_steps,
        }
    }

    fn build_db_2() -> Db {
        let all_cmds = vec![make_command(
            109,
            &[240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252, 253],
            "Stop file system fs",
        )];
        let all_jobs = vec![
            make_job(240, CmdId(109), &[], &[], "Stop target fs-OST0008"),
            make_job(241, CmdId(109), &[], &[], "Stop target fs-OST0007"),
            make_job(242, CmdId(109), &[], &[], "Stop target fs-OST0003"),
            make_job(243, CmdId(109), &[], &[], "Stop target fs-OST0000"),
            make_job(
                244,
                CmdId(109),
                &[],
                &[240, 241, 242, 243],
                "Make file system fs unavailable",
            ),
            make_job(245, CmdId(109), &[], &[244], "Stop target fs-OST0005"),
            make_job(246, CmdId(109), &[], &[244], "Stop target fs-MDT0000"),
            make_job(247, CmdId(109), &[], &[244], "Stop target fs-OST0004"),
            make_job(248, CmdId(109), &[], &[244], "Stop target fs-OST0002"),
            make_job(249, CmdId(109), &[], &[244], "Stop target fs-OST0001"),
            make_job(250, CmdId(109), &[], &[244], "Stop target fs-OST0006"),
            make_job(251, CmdId(109), &[], &[244], "Stop target fs-MDT0001"),
            make_job(252, CmdId(109), &[], &[244], "Stop target fs-OST0009"),
            make_job(
                253,
                CmdId(109),
                &[],
                &[240, 241, 242, 243, 244, 245, 246, 247, 248, 249, 250, 251, 252],
                "Stop file system fs",
            ),
        ];
        let all_steps = vec![];
        Db {
            all_cmds,
            all_jobs,
            all_steps,
        }
    }

    fn prepare_subset(db: &Db, cmd_ids: &[i32]) -> (Vec<Arc<Command>>, Vec<Arc<Job0>>, Vec<Arc<Step>>) {
        let cmds = db.select_cmds(&cmd_ids);
        let c_ids = cmds
            .iter()
            .map(|x| extract_ids::<Job0>(&x.jobs))
            .flatten()
            .collect::<Vec<i32>>();
        let jobs = db.select_jobs(&c_ids);
        let j_ids = jobs
            .iter()
            .map(|x| extract_ids::<Step>(&x.steps))
            .flatten()
            .collect::<Vec<i32>>();
        let steps = db.select_steps(&j_ids);
        let cmds = db.all_cmds.clone(); // use all roots
        (cmds, jobs, steps)
    }

    fn generate_random_selects<R: RngCore>(db: &Db, rng: &mut R, n: i32) -> Vec<Select> {
        let cmd_ids = db.all_cmds.iter().map(|x| x.id).collect::<Vec<_>>();
        let job_ids = db.all_jobs.iter().map(|x| x.id).collect::<Vec<_>>();
        let step_ids = db.all_steps.iter().map(|x| x.id).collect::<Vec<_>>();
        fn sample<R: RngCore>(rng: &mut R, ids: &[i32], m: usize) -> Vec<i32> {
            let mut hs = HashSet::with_capacity(m);
            let n = ids.len();
            if n < m {
                panic!("Must be m <= ids.len()")
            }
            for _ in 0..m {
                loop {
                    let id = ids[rng.next_u32() as usize % n];
                    if hs.insert(id) {
                        break;
                    }
                }
            }
            let mut sam = hs.into_iter().collect::<Vec<_>>();
            sam.sort();
            sam
        }
        (0..n)
            .into_iter()
            .map(|_| {
                let nc = (rng.next_u32() % 2 + 1) as usize;
                let nj = (rng.next_u32() % 4 + 1) as usize;
                let ns = (rng.next_u32() % 4 + 1) as usize;
                let sel_cmd_ids = sample(rng, &cmd_ids, nc);
                let sel_job_ids = sample(rng, &job_ids, nj);
                let sel_step_ids = sample(rng, &step_ids, ns);
                let result = sel_cmd_ids
                    .into_iter()
                    .map(|id| TypedId::Cmd(id))
                    .chain(sel_job_ids.into_iter().map(|id| TypedId::Job(id)))
                    .chain(sel_step_ids.into_iter().map(|id| TypedId::Step(id)))
                    .collect::<HashSet<_>>();
                Select(result)
            })
            .collect()
    }

    fn extract_ids<T: EndpointName>(uris: &[String]) -> Vec<i32> {
        // uris is the slice of strings like ["/api/step/123/", .. , "/api/step/234/"]
        uris.iter().filter_map(|s| extract_uri_id::<T>(s)).collect()
    }

    fn rich_job_to_string(node: Arc<RichJob>, is_new: bool, ctx: &mut Context0) -> String {
        ctx.level += 1;
        if is_new {
            format!("{}: {}\n", node.id, node.description)
        } else {
            String::new()
        }
    }

    fn rich_job_combine_strings(node: String, nodes: Vec<String>, ctx: &mut Context0) -> String {
        if ctx.level > 0 {
            ctx.level -= 1;
        }
        let space = if ctx.level > 0 { "  " } else { "" };
        let mut result = String::with_capacity(100);
        for line in node.lines() {
            result.push_str(space);
            result.push_str(line);
            result.push('\n');
        }
        for n in nodes.iter() {
            for line in n.lines() {
                result.push_str(space);
                result.push_str(line);
                result.push('\n');
            }
        }
        result
    }

    const WELL_ORDERED_TREE: &'static str = r#"253: Stop file system fs
  244: Make file system fs unavailable
    243: Stop target fs-OST0000
    242: Stop target fs-OST0003
    241: Stop target fs-OST0007
    240: Stop target fs-OST0008
  246: Stop target fs-MDT0000
  251: Stop target fs-MDT0001
  249: Stop target fs-OST0001
  248: Stop target fs-OST0002
  247: Stop target fs-OST0004
  245: Stop target fs-OST0005
  250: Stop target fs-OST0006
  252: Stop target fs-OST0009
"#;

    // test_view is here https://gist.github.com/nlinker/9cbd9092986180531a841f9e610ef53a
}
