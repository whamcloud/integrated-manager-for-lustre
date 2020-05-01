// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    components::{font_awesome::*, modal},
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
use std::{
    collections::{HashMap, HashSet},
    fmt::{self, Display},
    sync::Arc,
    time::Duration,
};

/// The component polls `/api/(command|job|step)/` endpoint and this constant defines how often it does.
const POLL_INTERVAL: Duration = Duration::from_millis(1000);

type Job0 = Job<Option<serde_json::Value>>;

type RichCommand = Rich<u32, Command>;
type RichJob = Rich<u32, Job0>;
type RichStep = Rich<u32, Step>;

type JobsGraph = DependencyDAG<u32, RichJob>;

#[derive(Copy, Clone, Hash, PartialEq, Eq, Ord, PartialOrd, Debug)]
pub struct CmdId(u32);

#[derive(Copy, Clone, Hash, PartialEq, Eq, Ord, PartialOrd, Debug)]
pub struct JobId(u32);

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum TypedId {
    Command(u32),
    Job(u32),
    Step(u32),
}

/// Note: all vectors must be sorted
#[derive(Clone, Eq, PartialEq, Debug)]
pub enum Select {
    None,
    Command(Vec<u32>),
    CommandJob(Vec<u32>, Vec<u32>),
    CommandJobSteps(Vec<u32>, Vec<u32>, Vec<u32>),
}

impl Default for Select {
    fn default() -> Self {
        Self::None
    }
}

impl Display for Select {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{:?}", self)
    }
}

#[derive(Clone, Debug)]
pub struct Context<'a> {
    pub steps_view: &'a HashMap<JobId, Vec<Arc<RichStep>>>,
    pub select: &'a Select,
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
    pub jobs_graphs: HashMap<CmdId, JobsGraph>, // cmd_id -> JobsGraph

    pub steps: HashMap<u32, Arc<RichStep>>,
    pub steps_view: HashMap<JobId, Vec<Arc<RichStep>>>, // job_id -> [Step]

    pub select: Select,
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
    Noop,
}

pub fn update(msg: Msg, model: &mut Model, orders: &mut impl Orders<Msg, GMsg>) {
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
                    model.assign_commands(temp_slice);
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
            model.commands_loading = false;
            match *commands_data_result {
                Ok(api_list) => {
                    model.assign_commands(api_list.objects);
                }
                Err(e) => {
                    error!(format!("Failed to fetch commands {:#?}", e));
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
                model.assign_jobs(api_list.objects);
            }
            Err(e) => {
                error!(format!("Failed to fetch jobs {:#?}", e));
                orders.skip();
            }
        },
        Msg::FetchedSteps(steps_data_result) => match *steps_data_result {
            Ok(api_list) => {
                model.assign_steps(api_list.objects);
            }
            Err(e) => {
                error!(format!("Failed to fetch steps {:#?}", e));
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
            let cmd_ids = extract_sorted_keys(&model.commands);
            orders
                .skip()
                .perform_cmd(fetch_the_batch(cmd_ids, |x| Msg::FetchedCommands(Box::new(x))));
        }
        Select::Command(cmd_ids) => {
            // the user has opened the info on the command,
            // we need the corresponding jobs to build the dependency graph
            let all_cmd_ids = extract_sorted_keys(&model.commands);
            let job_ids = cmd_ids
                .iter()
                .filter(|id| model.commands.contains_key(id))
                .flat_map(|id| model.commands[id].deps())
                .copied()
                .collect::<Vec<u32>>();
            orders
                .skip()
                .perform_cmd(fetch_the_batch(job_ids, |x| Msg::FetchedJobs(Box::new(x))))
                .perform_cmd(fetch_the_batch(all_cmd_ids, |x| Msg::FetchedCommands(Box::new(x))));
        }
        Select::CommandJob(cmd_ids, _) | Select::CommandJobSteps(cmd_ids, _, _) => {
            // the user has opened the info on the command and selected the corresponding job
            // or the user has opened the info on the command, selected a job and expanded some of the steps
            let all_cmd_ids = extract_sorted_keys(&model.commands);
            let job_ids = cmd_ids
                .iter()
                .filter(|id| model.commands.contains_key(id))
                .flat_map(|id| model.commands[id].deps())
                .copied()
                .collect::<Vec<u32>>();
            let step_ids = job_ids
                .iter()
                .filter(|id| model.jobs.contains_key(id))
                .flat_map(|id| model.jobs[id].deps())
                .copied()
                .collect::<Vec<u32>>();
            orders
                .skip()
                .perform_cmd(fetch_the_batch(step_ids, |x| Msg::FetchedSteps(Box::new(x))))
                .perform_cmd(fetch_the_batch(job_ids, |x| Msg::FetchedJobs(Box::new(x))))
                .perform_cmd(fetch_the_batch(all_cmd_ids, |x| Msg::FetchedCommands(Box::new(x))));
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
    let is_open = is_typed_id_selected(&model.select, TypedId::Command(x.id));
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
        let dag_view = job_dag_view(model, &model.jobs_graphs[&parent_cid]);
        div![
            class![C.font_ordinary, C.text_gray_700],
            h4![class![C.text_lg, C.font_medium], "Jobs"],
            div![class![C.p_1, C.pb_2, C.mb_1, C.overflow_auto], dag_view],
        ]
    }
}

pub fn job_dag_view(model: &Model, graph: &JobsGraph) -> Node<Msg> {
    fn build_node_view(graph: &JobsGraph, n: Arc<RichJob>, ctx: &mut Context) -> Node<Msg> {
        ctx.is_new = ctx.visited.insert(n.id);
        let parent: Node<Msg> = job_item_view(Arc::clone(&n), ctx);
        let mut acc: Vec<Node<Msg>> = Vec::new();
        if let Some(deps) = graph.links.get(&n.id) {
            if ctx.is_new {
                for d in deps {
                    let rec_node = build_node_view(graph, Arc::clone(d), ctx);
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
        steps_view: &model.steps_view,
        select: &model.select,
        visited: HashSet::new(),
        is_new: false,
    };
    let mut acc: Vec<Node<Msg>> = Vec::with_capacity(graph.roots.len());
    for r in &graph.roots {
        acc.push(build_node_view(graph, Arc::clone(r), &mut ctx));
    }
    div![acc]
}

fn job_item_view(job: Arc<RichJob>, ctx: &mut Context) -> Node<Msg> {
    if ctx.is_new {
        let icon = job_status_icon(job.as_ref());
        // we don't use job.deps() since deps() now show interdependencies between jobs
        if job.steps.is_empty() {
            span![span![class![C.mr_1], icon], span![job.description]]
        } else {
            let is_open = is_typed_id_selected(ctx.select, TypedId::Job(job.id));
            let def_vec = Vec::new();
            let steps = ctx.steps_view.get(&JobId(job.id)).unwrap_or(&def_vec);
            div![
                a![
                    span![class![C.mr_1], icon],
                    span![class![C.cursor_pointer, C.underline], job.description],
                    simple_ev(Ev::Click, Msg::Click(TypedId::Job(job.id))),
                ],
                step_list_view(steps, ctx.select, is_open),
            ]
        }
    } else {
        empty!()
    }
}

fn step_list_view(steps: &[Arc<RichStep>], select: &Select, is_open: bool) -> Node<Msg> {
    if !is_open {
        empty!()
    } else if steps.is_empty() {
        div![
            class![C.my_8, C.text_center, C.text_gray_500],
            font_awesome(class![C.w_8, C.h_8, C.inline, C.pulse], "spinner"),
        ]
    } else {
        div![ul![
            class![C.p_1, C.pb_2, C.mb_1, C.overflow_auto],
            steps.iter().map(|x| {
                let is_open = is_typed_id_selected(select, TypedId::Step(x.id));
                li![step_item_view(x, is_open)]
            })
        ]]
    }
}

fn step_item_view(step: &RichStep, is_open: bool) -> Vec<Node<Msg>> {
    let icon = step_status_icon(is_open);
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
                pre![&pre_class, args],
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

fn step_status_icon<T>(is_open: bool) -> Node<T> {
    let awesome_style = class![C.fill_current, C.w_4, C.h_4, C.inline, C.text_gray_500];
    if is_open {
        font_awesome_outline(awesome_style, "minus-square")
    } else {
        font_awesome_outline(awesome_style, "plus-square")
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
    let mut ids: Vec<_> = ids.into_iter().map(|x| ("id__in", x)).collect();
    ids.push(("limit", 0));
    match Request::api_query(T::endpoint_name(), &ids) {
        Ok(req) => req.fetch_json_data(data_to_msg).await,
        Err(_) => {
            // we always can url encode a vector of u32-s
            unreachable!("Cannot encode request for {} with params {:?}", T::endpoint_name(), ids)
        }
    }
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
        TypedId::Command(c) => match select {
            Select::None => false,
            Select::Command(cs) => cs.contains(&c),
            Select::CommandJob(cs, _) => cs.contains(&c),
            Select::CommandJobSteps(cs, _, _) => cs.contains(&c),
        },
        TypedId::Job(j) => match select {
            Select::None => false,
            Select::Command(_) => false,
            Select::CommandJob(_, js) => js.contains(&j),
            Select::CommandJobSteps(_, js, _) => js.contains(&j),
        },
        TypedId::Step(s) => match select {
            Select::None => false,
            Select::Command(_) => false,
            Select::CommandJob(_, _) => false,
            Select::CommandJobSteps(_, _, ss) => ss.contains(&s),
        },
    }
}

fn interpret_click(old_select: &Select, the_id: TypedId) -> (Select, bool) {
    if is_typed_id_selected(old_select, the_id) {
        (perform_close_click(old_select.clone(), the_id), false)
    } else {
        (perform_open_click(old_select.clone(), the_id), true)
    }
}

fn perform_open_click(cur_select: Select, the_id: TypedId) -> Select {
    fn insert_in_sorted(ids: &[u32], id: u32) -> Vec<u32> {
        let mut ids = ids.to_vec();
        match ids.binary_search(&id) {
            Ok(_) => ids,
            Err(pos) => {
                ids.insert(pos, id);
                ids
            }
        }
    }
    match the_id {
        TypedId::Command(c) => match cur_select {
            Select::None => Select::Command(vec![c]),
            Select::Command(cs) => Select::Command(insert_in_sorted(&cs, c)),
            Select::CommandJob(cs, js) => Select::CommandJob(insert_in_sorted(&cs, c), js),
            Select::CommandJobSteps(cs, js, ss) => Select::CommandJobSteps(insert_in_sorted(&cs, c), js, ss),
        },
        TypedId::Job(j) => match cur_select {
            Select::None => cur_select,
            Select::Command(cs) => Select::CommandJob(cs, vec![j]),
            Select::CommandJob(cs, js) => Select::CommandJob(cs, insert_in_sorted(&js, j)),
            Select::CommandJobSteps(cs, js, ss) => Select::CommandJobSteps(cs, insert_in_sorted(&js, j), ss),
        },
        TypedId::Step(s) => match cur_select {
            Select::None => cur_select,
            Select::Command(_) => cur_select,
            Select::CommandJob(cs, js) => Select::CommandJobSteps(cs, js, vec![s]),
            Select::CommandJobSteps(cs, js, ss) => Select::CommandJobSteps(cs, js, insert_in_sorted(&ss, s)),
        },
    }
}

fn perform_close_click(cur_select: Select, the_id: TypedId) -> Select {
    fn remove_from_sorted(ids: &[u32], id: u32) -> Vec<u32> {
        let mut ids = ids.to_vec();
        match ids.binary_search(&id) {
            Ok(pos) => {
                ids.remove(pos);
                ids
            }
            Err(_) => ids,
        }
    }
    match the_id {
        TypedId::Command(c) => match cur_select {
            Select::None => cur_select,
            Select::Command(cs) => {
                let ids = remove_from_sorted(&cs, c);
                if ids.is_empty() {
                    Select::None
                } else {
                    Select::Command(ids)
                }
            }
            Select::CommandJob(cs, js) => {
                let ids = remove_from_sorted(&cs, c);
                if ids.is_empty() {
                    Select::None
                } else {
                    Select::CommandJob(ids, js)
                }
            }
            Select::CommandJobSteps(cs, js, ss) => {
                let ids = remove_from_sorted(&cs, c);
                if ids.is_empty() {
                    Select::None
                } else {
                    Select::CommandJobSteps(ids, js, ss)
                }
            }
        },
        TypedId::Job(j) => match cur_select {
            Select::None => cur_select,
            Select::Command(_) => cur_select,
            Select::CommandJob(cids, jids) => {
                let ids = remove_from_sorted(&jids, j);
                if ids.is_empty() {
                    Select::Command(cids)
                } else {
                    Select::CommandJob(cids, ids)
                }
            }
            Select::CommandJobSteps(cs, js, ss) => {
                let ids = remove_from_sorted(&js, j);
                if ids.is_empty() {
                    Select::Command(cs)
                } else {
                    // note, steps can become not consistent now, but this is handled in other places
                    Select::CommandJobSteps(cs, ids, ss)
                }
            }
        },
        TypedId::Step(step_id) => match cur_select {
            Select::None => cur_select,
            Select::Command(_) => cur_select,
            Select::CommandJob(_, _) => cur_select,
            Select::CommandJobSteps(cs, js, ss) => {
                let ids = remove_from_sorted(&ss, step_id);
                if ids.is_empty() {
                    Select::CommandJob(cs, js)
                } else {
                    Select::CommandJobSteps(cs, js, ids)
                }
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

fn extract_sorted_keys<T>(hm: &HashMap<u32, T>) -> Vec<u32> {
    let mut ids = hm.keys().copied().collect::<Vec<_>>();
    ids.sort();
    ids
}

fn convert_to_sorted_vec<T: Clone>(hm: &HashMap<u32, T>) -> Vec<T> {
    extract_sorted_keys(hm).into_iter().map(|k| hm[&k].clone()).collect()
}

fn convert_to_rich_hashmap<T>(ts: Vec<T>, extract: impl Fn(&T) -> (u32, Vec<u32>)) -> HashMap<u32, Arc<Rich<u32, T>>> {
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
        self.commands_loading = true;
        self.commands.clear();
        self.commands_view.clear();
        self.jobs.clear();
        self.jobs_graphs.clear();
        self.steps.clear();
        self.steps_view.clear();
        self.select = Default::default();
    }

    fn assign_commands(&mut self, cmds: Vec<Command>) {
        self.commands = convert_to_rich_hashmap(cmds, extract_children_from_cmd);
        let tuple = self.check_back_consistency();
        self.refresh_view(tuple);
    }

    fn assign_jobs(&mut self, jobs: Vec<Job0>) {
        self.jobs = convert_to_rich_hashmap(jobs, extract_children_from_job);
        let tuple = self.check_back_consistency();
        self.refresh_view(tuple);
    }

    fn assign_steps(&mut self, steps: Vec<Step>) {
        self.steps = convert_to_rich_hashmap(steps, extract_children_from_step);
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
        match &self.select {
            Select::None => {}
            Select::Command(cs) => {
                ok[0] = ok[0] && is_subset(cs, &cmd_ids);
            }
            Select::CommandJob(cs, js) => {
                ok[0] = ok[0] && is_subset(cs, &cmd_ids);
                ok[1] = ok[1] && is_subset(js, &job_ids);
            }
            Select::CommandJobSteps(cs, js, ss) => {
                ok[0] = ok[0] && is_subset(cs, &cmd_ids);
                ok[1] = ok[1] && is_subset(js, &job_ids);
                ok[2] = ok[2] && is_subset(ss, &step_ids);
            }
        }
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
                    let jobs_graph_data = cmd
                        .deps()
                        .iter()
                        .map(|k| RichJob::new(self.jobs[k].inner.clone(), extract_wait_fors_from_job))
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
    use std::hash::Hash;
    use wasm_bindgen::__rt::core::fmt::Debug;

    #[derive(Default, Clone, Debug)]
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
    fn test_interpret_click() {
        // test transitions, we simulate the clicks on various elements

        let pair = (Select::Command(vec![77]), false);

        let pair = interpret_click(&pair.0, TypedId::Job(162));
        assert_eq!(&pair, &(Select::CommandJob(vec![77], vec![162]), true));

        let pair = interpret_click(&pair.0, TypedId::Job(163));
        assert_eq!(&pair, &(Select::CommandJob(vec![77], vec![162, 163]), true));

        let pair = interpret_click(&pair.0, TypedId::Step(309));
        assert_eq!(
            &pair,
            &(Select::CommandJobSteps(vec![77], vec![162, 163], vec![309]), true)
        );

        let pair = interpret_click(&pair.0, TypedId::Step(308));
        assert_eq!(
            &pair,
            &(Select::CommandJobSteps(vec![77], vec![162, 163], vec![308, 309]), true)
        );

        let pair = interpret_click(&pair.0, TypedId::Job(163));
        assert_eq!(
            &pair,
            &(Select::CommandJobSteps(vec![77], vec![162], vec![308, 309]), false)
        );

        let pair = interpret_click(&pair.0, TypedId::Job(162));
        assert_eq!(&pair, &(Select::Command(vec![77]), false));
    }

    /// There could the the problem, when `schedule_fetch_tree` made the api requests
    /// in one order, but during delays or something the responses may come in different
    /// order. In all such cases, however, model should remain consistent,
    /// and the test checks this.
    #[test]
    fn test_async_handlers_consistency() {
        let mut rng = Xoroshiro64Star::seed_from_u64(555);
        let db = build_db();
        let mut model = Model::default();
        let cmd_ids = db.all_cmds.iter().map(|x| x.id).collect::<Vec<_>>();
        let selects = generate_random_selects(&db, &mut rng, 1000);
        for select in selects {
            let sel_cmd_ids = match &select {
                Select::None => &cmd_ids,
                Select::Command(cs) | Select::CommandJob(cs, _) | Select::CommandJobSteps(cs, _, _) => &cs,
            };
            let (c, j, s) = prepare_subset(&db, sel_cmd_ids);
            model.clear();
            model.select = select.clone();
            model.assign_commands(c.clone());
            model.assign_jobs(j.clone());
            model.assign_steps(s.clone());
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
                        1 => model.assign_commands(c.clone()),
                        2 => model.assign_jobs(j.clone()),
                        3 => model.assign_steps(s.clone()),
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
            make_job(10, &[20, 21], &[11], "Ten"),
            make_job(11, &[21, 26], &[], "Eleven"),
            make_job(12, &[22, 23], &[13], "Twelve"),
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

    fn prepare_subset(db: &Db, cmd_ids: &[u32]) -> (Vec<Command>, Vec<Job0>, Vec<Step>) {
        let cmds = db.select_cmds(&cmd_ids);
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

    fn generate_random_selects<R: RngCore>(db: &Db, rng: &mut R, n: u32) -> Vec<Select> {
        let cmd_ids = db.all_cmds.iter().map(|x| x.id).collect::<Vec<_>>();
        let job_ids = db.all_jobs.iter().map(|x| x.id).collect::<Vec<_>>();
        let step_ids = db.all_steps.iter().map(|x| x.id).collect::<Vec<_>>();
        fn sample<R: RngCore>(rng: &mut R, ids: &[u32], m: usize) -> Vec<u32> {
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
            .map(|_| match rng.next_u32() % 9 {
                0 => Select::None,
                1 | 2 => {
                    let nc = (rng.next_u32() % 2 + 1) as usize;
                    let sel_cmd_ids = sample(rng, &cmd_ids, nc);
                    Select::Command(sel_cmd_ids)
                }
                3 | 4 | 5 => {
                    let nc = (rng.next_u32() % 2 + 1) as usize;
                    let nj = (rng.next_u32() % 4 + 1) as usize;
                    let sel_cmd_ids = sample(rng, &cmd_ids, nc);
                    let sel_job_ids = sample(rng, &job_ids, nj);
                    Select::CommandJob(sel_cmd_ids, sel_job_ids)
                }
                6 | 7 | 8 => {
                    let nc = (rng.next_u32() % 2 + 1) as usize;
                    let nj = (rng.next_u32() % 4 + 1) as usize;
                    let ns = (rng.next_u32() % 4 + 1) as usize;
                    let sel_cmd_ids = sample(rng, &cmd_ids, nc);
                    let sel_job_ids = sample(rng, &job_ids, nj);
                    let sel_step_ids = sample(rng, &step_ids, ns);
                    Select::CommandJobSteps(sel_cmd_ids, sel_job_ids, sel_step_ids)
                }
                _ => Select::None,
            })
            .collect()
    }

    fn extract_ids<T: EndpointName>(uris: &[String]) -> Vec<u32> {
        // uris is the slice of strings like ["/api/step/123/", .. , "/api/step/234/"]
        uris.iter().filter_map(|s| extract_uri_id::<T>(s)).collect()
    }
}
