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
use std::collections::{HashMap, HashSet};

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
pub enum Select {
    None,
    Command(u32),
    CommandJob(u32, u32),
    CommandJobSteps(u32, u32, Vec<u32>),
}

impl Default for Select {
    fn default() -> Self {
        Self::None
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

    pub commands: HashMap<u32, Arc<RichCommand>>,
    pub commands_view: Vec<Arc<RichCommand>>,

    pub jobs: HashMap<u32, Arc<RichJob>>,
    pub jobs_view: Vec<Arc<RichJob>>,
    pub jobs_graph: JobsGraph,

    pub steps: HashMap<u32, Arc<RichStep>>,
    pub steps_view: Vec<Arc<RichStep>>,

    pub select: Select,
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
    let msg_str = match msg {
        Msg::Modal(_) => "Msg-Modal".to_string(),
        Msg::FireCommands(_) => "Msg-FireCommands".to_string(),
        Msg::FetchTree => "Msg-FetchTree".to_string(),
        Msg::FetchedCommands(_) => "Msg-FetchedCommands".to_string(),
        Msg::FetchedJobs(_) => "Msg-FetchedJobs".to_string(),
        Msg::FetchedSteps(_) => "Msg-FetchedSteps".to_string(),
        Msg::Click(_) => "Msg-Click".to_string(),
        Msg::Noop => "Msg-Noop".to_string(),
    };
    log!(msg_str, model);
    match msg {
        Msg::Modal(msg) => {
            modal::update(msg, &mut model.modal, &mut orders.proxy(Msg::Modal));
        }
        Msg::FireCommands(cmds) => {
            model.select = Select::None;
            model.modal.open = true;

            // clear model from the previous command modal work
            model.clear();
            match cmds {
                Input::Commands(cmds) => {
                    // use the (little) optimization:
                    // if we already have the commands and they all finished, we don't need to poll them anymore
                    let temp_slice = cmds.iter().map(|x: &Arc<Command>| (**x).clone()).collect::<Vec<_>>();
                    model.assign_commands(&temp_slice);
                    if !is_all_finished(&model.commands) {
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
            if !is_all_finished(&model.commands) {
                schedule_fetch_tree(model, orders);
            }
        }
        Msg::FetchedCommands(commands_data_result) => {
            match *commands_data_result {
                Ok(api_list) => {
                    model.assign_commands(&api_list.objects);
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
                model.assign_jobs(&api_list.objects);
            }
            Err(e) => {
                error!("Failed to perform fetch_job_status {:#?}", e);
                orders.skip();
            }
        },
        Msg::FetchedSteps(steps_data_result) => match *steps_data_result {
            Ok(api_list) => {
                model.assign_steps(&api_list.objects);
            }
            Err(e) => {
                error!("Failed to perform fetch_job_status {:#?}", e);
                orders.skip();
            }
        },
        Msg::Click(the_id) => {
            let (select, do_fetch) = interpret_click(&model.select, the_id);
            model.select = select;
            if do_fetch {
                schedule_fetch_tree(model, orders);
            }
        }
        Msg::Noop => {}
    }
}

fn schedule_fetch_tree(model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
    match &model.select {
        Select::None => {
            // the user has all the commands dropdowns closed
            let cmd_ids = extract_sorted_ids(&model.commands);
            orders
                .skip()
                .perform_cmd(fetch_the_batch(cmd_ids, |x| Msg::FetchedCommands(Box::new(x))));
        }
        Select::Command(cmd_id) => {
            // the user has opened the info on the command,
            // we need the corresponding jobs to build the dependency graph
            let cmd_ids = extract_sorted_ids(&model.commands);
            let job_ids = model.commands[cmd_id].deps().to_vec();
            orders
                .skip()
                .perform_cmd(fetch_the_batch(job_ids, |x| Msg::FetchedJobs(Box::new(x))))
                .perform_cmd(fetch_the_batch(cmd_ids, |x| Msg::FetchedCommands(Box::new(x))));
        }
        Select::CommandJob(cmd_id, job_id) | Select::CommandJobSteps(cmd_id, job_id, _) => {
            // the user has opened the info on the command and selected the corresponding job
            // or the user has opened the info on the command, selected a job and expanded some of the steps
            let cmd_ids = extract_sorted_ids(&model.commands);
            let job_ids = model.commands[cmd_id].deps().to_vec();
            let step_ids = model.jobs[job_id].deps().to_vec();
            orders
                .skip()
                .perform_cmd(fetch_the_batch(step_ids, |x| Msg::FetchedSteps(Box::new(x))))
                .perform_cmd(fetch_the_batch(job_ids, |x| Msg::FetchedJobs(Box::new(x))))
                .perform_cmd(fetch_the_batch(cmd_ids, |x| Msg::FetchedCommands(Box::new(x))));
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
                    let mut ids = model.commands.keys().copied().collect::<Vec<_>>();
                    ids.sort();
                    vec![
                        modal::title_view(Msg::Modal, plain!["Commands"]),
                        div![
                            class![C.py_8],
                            ids.iter().map(|k| { command_item_view(model, &model.commands[k]) })
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
    let is_open = is_typed_id_selected(&model.select, TypedId::Command(x.id));
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
    let step_list = step_list_view(&model.select, &model.steps);
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

fn step_list_view(select: &Select, steps: &HashMap<u32, Arc<RichStep>>) -> Node<Msg> {
    if steps.is_empty() {
        empty!()
    } else {
        let mut ids = steps.keys().copied().collect::<Vec<_>>();
        ids.sort();
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
            ids.iter().map(|k| {
                let is_open = is_typed_id_selected(select, TypedId::Step(*k));
                li![step_item_view(&steps[k], is_open)]
            })
        ]]
    }
}

fn step_item_view(step: &RichStep, is_open: bool) -> Vec<Node<Msg>> {
    let icon = step_status_icon(step, is_open);
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

fn is_finished(cmd: &RichCommand) -> bool {
    cmd.complete
}

fn is_all_finished(cmds: &HashMap<u32, Arc<RichCommand>>) -> bool {
    cmds.values().all(|c| is_finished(c))
}

fn is_typed_id_selected(select: &Select, typed_id: TypedId) -> bool {
    match typed_id {
        TypedId::Command(cmd_id) => match select {
            Select::None => false,
            Select::Command(cid) => cmd_id == *cid,
            Select::CommandJob(cid, _) => cmd_id == *cid,
            Select::CommandJobSteps(cid, _, _) => cmd_id == *cid,
        },
        TypedId::Job(job_id) => match select {
            Select::None => false,
            Select::Command(_) => false,
            Select::CommandJob(_, jid) => job_id == *jid,
            Select::CommandJobSteps(_, jid, _) => job_id == *jid,
        },
        TypedId::Step(step_id) => match select {
            Select::None => false,
            Select::Command(_) => false,
            Select::CommandJob(_, _) => false,
            Select::CommandJobSteps(_, _, sids) => sids.contains(&step_id),
        },
    }
}

fn interpret_click(old_select: &Select, the_id: TypedId) -> (Select, bool) {
    // commands behave like radio-button with the
    // jobs behave like radio button
    // steps are set of independent checkboxes
    if is_typed_id_selected(old_select, the_id) {
        (perform_close_click(old_select, the_id), false)
    } else {
        (perform_open_click(old_select, the_id), true)
    }
}

fn perform_open_click(cur_select: &Select, the_id: TypedId) -> Select {
    match the_id {
        TypedId::Command(cmd_id) => Select::Command(cmd_id),
        TypedId::Job(job_id) => match &cur_select {
            Select::None => cur_select.clone(),
            Select::Command(cmd_id_0) => Select::CommandJob(*cmd_id_0, job_id),
            Select::CommandJob(cmd_id_0, _) => Select::CommandJob(*cmd_id_0, job_id),
            Select::CommandJobSteps(cmd_id_0, _, _) => Select::CommandJob(*cmd_id_0, job_id),
        },
        TypedId::Step(step_id) => match &cur_select {
            Select::None => cur_select.clone(),
            Select::Command(_) => cur_select.clone(),
            Select::CommandJob(cmd_id_0, job_id_0) => Select::CommandJobSteps(*cmd_id_0, *job_id_0, vec![step_id]),
            Select::CommandJobSteps(cmd_id_0, job_id_0, step_ids_0) => {
                if step_ids_0.contains(&step_id) {
                    Select::CommandJobSteps(*cmd_id_0, *job_id_0, step_ids_0.clone())
                } else {
                    let mut step_ids = step_ids_0.clone();
                    step_ids.push(step_id);
                    Select::CommandJobSteps(*cmd_id_0, *job_id_0, step_ids)
                }
            }
        },
    }
}

fn perform_close_click(cur_select: &Select, the_id: TypedId) -> Select {
    match the_id {
        TypedId::Command(_cmd_id) => Select::None,
        TypedId::Job(job_id) => match &cur_select {
            Select::None => cur_select.clone(),
            Select::Command(_cmd_id_0) => cur_select.clone(),
            Select::CommandJob(cmd_id_0, job_id_0) => {
                if job_id == *job_id_0 {
                    Select::Command(*cmd_id_0)
                } else {
                    cur_select.clone()
                }
            }
            Select::CommandJobSteps(cmd_id_0, job_id_0, _) => {
                if job_id == *job_id_0 {
                    Select::Command(*cmd_id_0)
                } else {
                    cur_select.clone()
                }
            }
        },
        TypedId::Step(step_id) => match &cur_select {
            Select::None => cur_select.clone(),
            Select::Command(_) => cur_select.clone(),
            Select::CommandJob(_, _) => cur_select.clone(),
            Select::CommandJobSteps(cmd_id_0, job_id_0, step_ids_0) => {
                // if the clicked step_id is contained in the list of open steps, just remove it
                let step_ids = step_ids_0.iter().copied().filter(|sid| *sid != step_id).collect();
                Select::CommandJobSteps(*cmd_id_0, *job_id_0, step_ids)
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

const fn extract_children_from_step(step: &Step) -> (u32, Vec<u32>) {
    (step.id, Vec::new()) // steps have no descendants
}

fn extract_wait_fors_from_job(job: &Job0) -> (u32, Vec<u32>) {
    // interdependencies between jobs
    (
        job.id,
        job.wait_for.iter().filter_map(|s| extract_uri_id::<Job0>(s)).collect(),
    )
}

fn extract_sorted_ids<T>(hm: &HashMap<u32, T>) -> Vec<u32> {
    let mut ids = hm.keys().copied().collect::<Vec<_>>();
    ids.sort();
    ids
}

fn convert_to_sorted_vec<T: Clone>(hm: &HashMap<u32, T>) -> Vec<T> {
    extract_sorted_ids(hm).into_iter().map(|k| hm[&k].clone()).collect()
}

fn convert_to_rich_hashmap<T: Clone>(
    ts: Vec<T>,
    extract: impl Fn(&T) -> (u32, Vec<u32>),
) -> HashMap<u32, Arc<Rich<u32, T>>> {
    ts.into_iter()
        .map(|t| {
            let (id, deps) = extract(&t);
            (id, Arc::new(Rich { id, deps, inner: t }))
        })
        .collect()
}

impl Model {
    fn clear(&mut self) {
        self.commands.clear();
        self.commands_view.clear();
        self.jobs.clear();
        self.jobs_view.clear();
        self.jobs_graph.clear();
        self.steps.clear();
        self.steps_view.clear();
        self.select = Default::default();
    }

    fn assign_commands(&mut self, cmds: &[Command]) {
        let mut sorted_cmds = cmds.to_vec();
        sorted_cmds.sort_by_key(|x| x.id);
        self.commands = convert_to_rich_hashmap(sorted_cmds, extract_children_from_cmd);
        let tuple = self.check_consistency(&self.select);
        self.refresh_view(tuple);
    }

    fn assign_jobs(&mut self, jobs: &[Job0]) {
        let mut sorted_jobs = jobs.to_vec();
        sorted_jobs.sort_by_key(|x| x.id);
        self.jobs = convert_to_rich_hashmap(sorted_jobs, extract_children_from_job);
        let tuple = self.check_consistency(&self.select);
        self.refresh_view(tuple);
    }

    fn assign_steps(&mut self, steps: &[Step]) {
        let mut sorted_steps = steps.to_vec();
        sorted_steps.sort_by_key(|x| x.id);
        self.steps = convert_to_rich_hashmap(sorted_steps, extract_children_from_step);
        let tuple = self.check_consistency(&self.select);
        self.refresh_view(tuple);
    }

    /// We perform the consistency check of the current collections
    /// `self.commands`, `self.jobs` and `self.steps`.
    /// The selection, if it is non-empty, places additional constraints.
    fn check_consistency(&self, select: &Select) -> (bool, bool, bool) {
        let mut ls = [false; 3];

        // check between layers
        let job_ids = extract_sorted_ids(&self.jobs);
        let step_ids = extract_sorted_ids(&self.steps);
        ls[0] = !self.commands.is_empty();
        ls[1] = self.commands.values().any(|x| x.deps() == &job_ids[..]);
        ls[2] = self.jobs.values().any(|x| x.deps() == &step_ids[..]);

        // the additional constraints from the selection
        match select {
            Select::None => {}
            Select::Command(i) => {
                let a0 = self.commands.get(i);
                if a0.is_some() {
                    ls[0] = true;
                }
            }
            Select::CommandJob(i, j) => {
                let a0 = self.commands.get(i);
                let b0 = self.jobs.get(j);
                match (a0, b0) {
                    (Some(a), Some(_)) => {
                        ls[0] = true;
                        ls[1] = a.deps().contains(j);
                    }
                    (Some(_), _) => {
                        ls[0] = true;
                    }
                    (_, _) => {}
                }
            }
            Select::CommandJobSteps(i, j, ks) => {
                let a0 = self.commands.get(i);
                let b0 = self.jobs.get(j);
                let cs = ks.iter().all(|k| self.steps.contains_key(k));
                let c0 = if cs { None } else { Some(()) };
                match (a0, b0, c0) {
                    (Some(a), Some(b), Some(_)) => {
                        ls[0] = true;
                        ls[1] = a.deps().contains(j);
                        ls[2] = ks.iter().all(|k| b.deps().contains(k));
                    }
                    (Some(a), Some(_), _) => {
                        ls[0] = true;
                        ls[1] = a.deps().contains(j);
                    }
                    (Some(_), _, _) => {
                        ls[0] = true;
                    }
                    (_, _, _) => {}
                }
            }
        }
        (ls[0], ls[1], ls[2])
    }

    fn refresh_view(&mut self, level: (bool, bool, bool)) {
        let (cmds_ok, jobs_ok, steps_ok) = level;
        if cmds_ok {
            self.commands_view = convert_to_sorted_vec(&self.commands);
        }
        if jobs_ok {
            self.jobs_view = convert_to_sorted_vec(&self.jobs);
            let jobs_graph_data = self
                .jobs_view
                .iter()
                .map(|x| RichJob::new(x.inner.clone(), extract_wait_fors_from_job))
                .collect::<Vec<RichJob>>();
            self.jobs_graph = build_direct_dag(&jobs_graph_data);
        }
        if steps_ok {
            self.steps_view = convert_to_sorted_vec(&self.steps);
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::dependency_tree::build_direct_dag;

    #[derive(Debug, Default, Clone)]
    struct Db {
        all_cmds: Vec<Command>,
        all_jobs: Vec<Job0>,
        all_steps: Vec<Step>,
    }

    impl Db {
        fn select_cmds(&self, is: &[u32]) -> Vec<Command> {
            self.all_cmds
                .iter()
                .filter(|x| is.contains(&x.id))
                .map(|x| x.clone())
                .collect()
        }
        fn select_jobs(&self, is: &[u32]) -> Vec<Job0> {
            self.all_jobs
                .iter()
                .filter(|x| is.contains(&x.id))
                .map(|x| x.clone())
                .collect()
        }
        fn select_steps(&self, is: &[u32]) -> Vec<Step> {
            self.all_steps
                .iter()
                .filter(|x| is.contains(&x.id))
                .map(|x| x.clone())
                .collect()
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
        // make jobs to have fake steps for the full jobs dom
        let jobs = vec![
            make_job(1, &[10], &[2, 3], "One"),
            make_job(2, &[11], &[], "Two"),
            make_job(3, &[12], &[], "Three"),
        ];
        let rich_jobs = jobs
            .into_iter()
            .map(|j| RichJob::new(j, extract_wait_fors_from_job))
            .collect::<Vec<RichJob>>();
        let dag = build_direct_dag(&rich_jobs);
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
        let start = Select::None;

        // click on Command(12)
        let triple = interpret_click(&start, TypedId::Command(12));
        assert_eq!(&triple, &(Select::Command(12), true));

        // click on Job(40)
        let triple = interpret_click(&triple.0, TypedId::Job(40));
        assert_eq!(&triple, &(Select::CommandJob(12, 40), true));

        // click on Step(63)
        let triple = interpret_click(&triple.0, TypedId::Step(63));
        assert_eq!(&triple, &(Select::CommandJobSteps(12, 40, vec![63]), true));

        // click on Step(62)
        let triple = interpret_click(&triple.0, TypedId::Step(62));
        assert_eq!(&triple, &(Select::CommandJobSteps(12, 40, vec![63, 62]), true));

        // click on the different command, Command(54)
        let triple = interpret_click(&triple.0, TypedId::Command(54));
        assert_eq!(&triple, &(Select::Command(54), true));

        // click on the Job(91)
        let triple = interpret_click(&triple.0, TypedId::Job(91));
        assert_eq!(&triple, &(Select::CommandJob(54, 91), true));

        // click on the different command, Command(12)
        let triple = interpret_click(&triple.0, TypedId::Command(12));
        assert_eq!(&triple, &(Select::Command(12), true));
    }

    /// There could the the problem, when `schedule_fetch_tree` made the api requests
    /// in one order, but during delays or something the responses may come in different
    /// order. In all such cases, however, model should remain consistent,
    /// and the test checks this.
    #[test]
    fn test_async_handlers_consistency() {
        fn extract_ids<T: Deps<u32>>(ts: &[Arc<T>]) -> Vec<u32> {
            ts.iter().map(|t| t.id()).collect()
        }

        let db = build_db();
        let mut model = Model::default();
        let (a, b, c) = prepare_subset(&db, 1);
        model.assign_commands(&db.select_cmds(&vec![1, 2]));
        model.assign_jobs(&db.select_jobs(&vec![10, 12, 13, 14]));
        model.assign_steps(&db.select_steps(&vec![20, 23, 14]));
        model.assign_commands(&db.select_cmds(&vec![1, 2, 3, 4]));

        // [1]
        model.select = Select::Command(1);
        model.assign_steps(&c);
        model.assign_jobs(&b);
        model.assign_commands(&a);
        assert_eq!(extract_ids(&model.commands_view), vec![1, 2, 3, 4]);
        assert_eq!(extract_ids(&model.jobs_view), vec![10, 11]);
        assert_eq!(extract_ids(&model.steps_view), Vec::<u32>::new());

        model.select = Select::CommandJob(1, 11);
        model.assign_steps(&c);
        model.assign_commands(&a);
        model.assign_jobs(&b);
        assert_eq!(extract_ids(&model.commands_view), vec![1, 2, 3, 4]);
        assert_eq!(extract_ids(&model.jobs_view), vec![10, 11]);
        assert_eq!(extract_ids(&model.steps_view), Vec::<u32>::new());

        model.select = Select::CommandJobSteps(1, 11, vec![26]);
        model.assign_jobs(&b);
        model.assign_steps(&c);
        model.assign_commands(&a);
        assert_eq!(extract_ids(&model.commands_view), vec![1, 2, 3, 4]);
        assert_eq!(extract_ids(&model.jobs_view), vec![10, 11]);
        assert_eq!(extract_ids(&model.steps_view), Vec::<u32>::new());
    }

    fn make_command(id: u32, jobs: &[u32], msg: &str) -> Command {
        Command {
            cancelled: false,
            complete: false,
            created_at: "2020-03-16T07:22:34.491600".to_string(),
            errored: false,
            id,
            jobs: jobs.iter().map(|x| format!("/api/job/{}/", x)).collect(),
            logs: "".to_string(),
            message: msg.to_string(),
            resource_uri: format!("/api/command/{}/", id),
        }
    }

    fn make_job(id: u32, steps: &[u32], wait_for: &[u32], descr: &str) -> Job0 {
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
            steps: steps.iter().map(|x| format!("/api/step/{}/", x)).collect(),
            wait_for: wait_for.iter().map(|x| format!("/api/job/{}/", x)).collect(),
            write_locks: vec![],
        }
    }

    fn make_step(id: u32, class_name: &str) -> Step {
        Step {
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
        }
    }

    fn build_db() -> Db {
        let all_cmds = vec![
            make_command(1, &[10, 11], "One"),
            make_command(2, &[12, 13], "Two"),
            make_command(3, &[14, 15], "Three"),
            make_command(4, &[16, 17], "Four"),
        ];
        let all_jobs = vec![
            make_job(10, &[20, 21], &[], "Ten"),
            make_job(11, &[21, 26], &[], "Eleven"),
            make_job(12, &[22, 23], &[], "Twelve"),
            make_job(13, &[23, 28], &[], "Thirteen"),
            make_job(14, &[24, 15], &[], "Ten"),
            make_job(15, &[25, 20], &[], "Eleven"),
            make_job(16, &[26, 27], &[], "Twelve"),
            make_job(17, &[27, 22], &[], "Thirteen"),
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

    fn prepare_subset(db: &Db, id: u32) -> (Vec<Command>, Vec<Job0>, Vec<Step>) {
        let cmds = db.select_cmds(&vec![id]);
        let c_ids = cmds
            .iter()
            .map(|x| extract_ids::<Job0>(&x.jobs))
            .flatten()
            .collect::<Vec<u32>>();
        let jobs = db.select_jobs(&c_ids);
        let j_ids = jobs
            .iter()
            .map(|x| extract_ids::<Step>(&x.steps))
            .flatten()
            .collect::<Vec<u32>>();
        let steps = db.select_steps(&j_ids);
        let cmds = db.all_cmds.clone(); // use all roots
        (cmds, jobs, steps)
    }

    fn extract_ids<T: EndpointName>(uris: &[String]) -> Vec<u32> {
        // uris is the slice of strings like ["/api/step/123/", .. , "/api/step/234/"]
        uris.iter().filter_map(|s| extract_uri_id::<T>(s)).collect()
    }
}
