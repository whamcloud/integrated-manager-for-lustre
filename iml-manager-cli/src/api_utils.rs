// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    display_utils::{self, display_cmd_state, wrap_fut},
    error::ImlManagerCliError,
};
use futures::{channel::mpsc, future, FutureExt, StreamExt, TryFutureExt};
use iml_command_utils::{wait_for_cmds_progress, Progress};
use iml_wire_types::{ApiList, AvailableAction, Command, EndpointName, FlatQuery, Host};
use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
use std::{collections::HashMap, fmt::Debug, time::Duration};
use tokio::{task::spawn_blocking, time::delay_for};

const ARROW: &'_ str = " ═➤ "; // variants: = ═ - ▬ > ▷ ▶ ► ➤
const SPACE: &'_ str = "   ";
const FETCH_DELAY_MS: u64 = 1000;
const SHOW_DELAY_MS: u64 = 200;

pub type Job0 = Job<Option<serde_json::Value>>;
pub type RichCommand = Rich<i32, Arc<Command>>;
pub type RichJob = Rich<i32, Arc<Job0>>;
pub type RichStep = Rich<i32, Arc<Step>>;

#[derive(Copy, Clone, Hash, PartialEq, Eq, Ord, PartialOrd, Debug)]
pub struct CmdId(i32);

#[derive(Copy, Clone, Hash, PartialEq, Eq, Ord, PartialOrd, Debug)]
pub struct JobId(i32);

// region declaration of types TypeId, State, Item<K>
#[derive(Copy, Clone, Hash, PartialEq, Eq, Debug)]
pub enum TypedId {
    Cmd(i32),
    Job(i32),
    Step(i32),
}

impl Default for TypedId {
    fn default() -> Self {
        TypedId::Cmd(0)
    }
}

impl Display for TypedId {
    fn fmt(&self, f: &mut Formatter<'_>) -> fmt::Result {
        match self {
            TypedId::Cmd(i) => write!(f, "c{}", i),
            TypedId::Job(i) => write!(f, "j{}", i),
            TypedId::Step(i) => write!(f, "s{}", i),
        }
    }
}

#[derive(Copy, Clone, Debug, Eq, PartialEq)]
pub enum State {
    Progressing,
    Cancelled,
    Completed,
    Errored,
}

impl Display for State {
    fn fmt(&self, f: &mut Formatter<'_>) -> fmt::Result {
        // consider for Cancelled this: `style("⟲").yellow()`
        match self {
            State::Progressing => write!(f, "{}", style("⠶").cyan()),
            State::Cancelled => write!(f, "{}", style("🚫")),
            State::Completed => write!(f, "{}", style("✔").green()),
            State::Errored => write!(f, "{}", style("✗").red()),
        }
    }
}

impl Default for State {
    fn default() -> Self {
        // return least priority element
        State::Progressing
    }
}

impl PartialOrd for State {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for State {
    /// States are ordered by priority. When combining two states (e.g. when collapsing the tree),
    /// the states with the higher priority are propagated up so any failures are not hidden.
    fn cmp(&self, other: &Self) -> Ordering {
        fn order(s: &State) -> u32 {
            match s {
                State::Progressing => 0,
                State::Completed => 1,
                State::Cancelled => 2,
                State::Errored => 3,
            }
        }
        Ord::cmp(&order(self), &order(other))
    }
}

#[derive(Clone, Eq, PartialEq, Debug)]
pub struct Payload {
    pub state: State,
    pub msg: String,
    pub backtrace: String,
    pub console: String,
    pub log: String,
}

impl Display for Payload {
    fn fmt(&self, f: &mut Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.msg)
    }
}

impl HasState for Payload {
    type State = State;
    fn state(&self) -> Self::State {
        self.state
    }
}

/// It is pretty expensive to set the style on the progress bar on each iteration,
/// so we need to keep track what the style and whether it has been set for the progress bar.
/// See [`set_progress_bar_message`] function.
#[derive(Clone, Debug)]
pub struct ProgressBarIndicator {
    pub progress_bar: ProgressBar,
    pub active_style: Cell<Option<bool>>,
}
// endregion

#[derive(serde::Serialize)]
pub struct SendJob<T> {
    pub class_name: String,
    pub args: T,
}

#[derive(serde::Serialize)]
pub struct SendCmd<T> {
    pub jobs: Vec<SendJob<T>>,
    pub message: String,
}

pub async fn create_command<T: serde::Serialize>(
    cmd_body: SendCmd<T>,
) -> Result<Command, ImlManagerCliError> {
    let resp = post(Command::endpoint_name(), cmd_body)
        .await?
        .error_for_status()?;

    let cmd = resp.json().await?;

    tracing::debug!("Resp JSON is {:?}", cmd);

    Ok(cmd)
}

pub fn cmd_state(cmd: &Command) -> State {
    if cmd.cancelled {
        State::Cancelled
    } else if cmd.errored {
        State::Errored
    } else if cmd.complete {
        State::Completed
    } else {
        State::Progressing
    }
}

pub fn job_state(job: &Job0) -> State {
    // job.state can be "pending", "tasked" or "complete"
    // if a job is errored or cancelled, it is also complete
    if job.cancelled {
        State::Cancelled
    } else if job.errored {
        State::Errored
    } else if job.state == "complete" {
        State::Completed
    } else {
        State::Progressing
    }
}

pub fn step_state(step: &Step) -> State {
    // step.state can be "success", "failed" or "incomplete"
    match &step.state[..] {
        "cancelled" => State::Cancelled,
        "failed" => State::Errored,
        "success" => State::Completed,
        _ /* "incomplete" */ => State::Progressing,
    }
}

fn cmd_finished(cmd: &Command) -> bool {
    cmd_state(cmd) == State::Completed
}

fn job_finished(job: &Job0) -> bool {
    job_state(job) == State::Completed
}

fn step_finished(step: &Step) -> bool {
    step_state(step) != State::Progressing
}

pub async fn wait_for_command(cmd: Command) -> Result<Command, ImlManagerCliError> {
    loop {
        if cmd_finished(&cmd) {
            return Ok(cmd);
        }

        delay_for(Duration::from_millis(1000)).await;

        let client = iml_manager_client::get_client()?;

        let cmd = iml_manager_client::get(
            client,
            &format!("command/{}", cmd.id),
            Vec::<(String, String)>::new(),
        )
        .await?;

        if cmd_finished(&cmd) {
            return Ok(cmd);
        }
    }
}

/// Waits for command completion and prints a spinner during progression.
/// When completed, prints the final command state
pub async fn wait_for_cmd_display(cmd: Command) -> Result<Command, ImlManagerCliError> {
    let cmd = wrap_fut(&cmd.message.to_string(), wait_for_cmd(cmd)).await?;

    display_cmd_state(&cmd);

    Ok(cmd)
}

pub async fn fetch_api_list<T>(ids: Vec<i32>) -> Result<ApiList<T>, ImlManagerCliError>
where
    T: EndpointName + serde::de::DeserializeOwned + std::fmt::Debug,
{
    let query: Vec<_> = ids
        .into_iter()
        .map(|x| ["id__in".into(), x.to_string()])
        .chain(iter::once(["limit".into(), "0".into()]))
        .collect();
    get(T::endpoint_name(), query).await
}

/// Waits for command completion and prints progress messages
/// This *does not* error on command failure, it only tracks command
/// completion
pub async fn wait_for_commands(commands: &[Command]) -> Result<Vec<Command>, ImlManagerCliError> {
    let multi_progress = Arc::new(MultiProgress::new());
    multi_progress.set_draw_target(ProgressDrawTarget::stdout());
    let sty_main = ProgressStyle::default_bar().template("{bar:60.green/yellow} {pos:>4}/{len:4}");
    let main_pb = multi_progress.add(ProgressBar::new(commands.len() as u64));
    main_pb.set_style(sty_main);
    main_pb.tick();

    // `current_items` will have only commands at first
    // and then will be extended after `fetch_and_update` succeeds
    let (cmd_ids, cmds) = build_initial_commands(commands);
    let tree = build_fresh_tree(&cmd_ids, &cmds, &HashMap::new(), &HashMap::new());
    let mut fresh_items = tree.render();
    let mut current_items_vec = Vec::new();
    calculate_and_apply_diff(
        &mut current_items_vec,
        &mut fresh_items,
        &tree,
        &multi_progress,
        &main_pb,
    );

    let is_done = Arc::new(AtomicBool::new(false));
    let current_items = Arc::new(tokio::sync::Mutex::new(current_items_vec));

    // multi-progress waiting loop
    // fut1: ErrInto<Map<JoinHandle<Result<()>>, fn(Result<Result<(), Error>, JoinError>)
    let fut1 = {
        let multi_progress = Arc::clone(&multi_progress);
        spawn_blocking(move || multi_progress.join())
            .map(|r: Result<Result<(), std::io::Error>, JoinError>| {
                r.map_err(|e: JoinError| e.into())
                    .and_then(std::convert::identity)
            })
            .err_into()
    };

    let fut = spawn_blocking(move || m.join())
        .err_into::<ImlManagerCliError>()
        .map(|x| x.and_then(|x| x.map_err(|e| e.into())));

    let (tx, rx) = mpsc::unbounded();

    let fut2 = rx
        .fold(cmd_spinners, |mut cmd_spinners, x| {
            match x {
                Progress::Update(x) => {
                    let pb = cmd_spinners.get(&x).unwrap();
                    pb.inc(1);
                }
                Progress::Complete(x) => {
                    let pb = cmd_spinners.remove(&x.id).unwrap();
                    pb.finish_with_message(&display_utils::format_cmd_state(&x));
                }
            }

            future::ready(cmd_spinners)
        })
        .never_error()
        .err_into::<ImlManagerCliError>();

    let fut3 = wait_for_cmds_progress(cmds, Some(tx)).err_into::<ImlManagerCliError>();

    let (_, _, xs) = future::try_join3(fut, fut2, fut3).await?;

/*
    // multi-progress waiting loop
    // fut1: ErrInto<Map<JoinHandle<Result<()>>, fn(Result<Result<(), Error>, JoinError>)
    let fut1 = {
        let multi_progress = Arc::clone(&multi_progress);
        spawn_blocking(move || multi_progress.join())
            .map(|r: Result<Result<(), std::io::Error>, JoinError>| {
                r.map_err(|e: JoinError| e.into())
                    .and_then(std::convert::identity)
            })
            .err_into()
    };

    // updating loop
    // fut2: impl Future<Output=Result<Vec<Command>, JoinError>>
    let fut2 = {
        let is_done = Arc::clone(&is_done);
        let multi_progress = Arc::clone(&multi_progress);
        let current_items = Arc::clone(&current_items);
        async move {
            let mut cmds: HashMap<i32, RichCommand> = cmds;
            let mut jobs: HashMap<i32, RichJob> = HashMap::new();
            let mut steps: HashMap<i32, RichStep> = HashMap::new();

            loop {
                if cmds
                    .values()
                    .all(|cmd| cmd_state(cmd) != State::Progressing)
                {
                    tracing::debug!("All commands complete. Returning");
                    for it in current_items.lock().await.iter() {
                        if let Some(indi) = it.indicator.as_ref() {
                            indi.progress_bar.finish();
                        }
                    }
                    main_pb.finish();
                    is_done.store(true, std::sync::atomic::Ordering::SeqCst);

                    // Unfortunately, there is no easy safe way to move out from Arc, so `clone`
                    // may be needed.
                    let mut commands: Vec<Command> = Vec::with_capacity(cmds.len());
                    for id in cmd_ids {
                        if let Some(rich_cmd) = cmds.remove(&id) {
                            match Arc::try_unwrap(rich_cmd.inner) {
                                Ok(cmd) => commands.push(cmd),
                                Err(arc_cmd) => commands.push((*arc_cmd).clone()),
                            }
                        }
                    }
                    return Ok::<_, ImlManagerCliError>(commands);
                }

                if let Err(e) = fetch_and_update(&mut cmds, &mut jobs, &mut steps).await {
                    // network call goes here, in case of lost connection we don't want to abort
                    // the cycle, but continue trying instead, the user can Ctrl+C anyway
                    main_pb.println(format!("Connection error: {}", style(e).red()));
                }

                let tree = build_fresh_tree(&cmd_ids, &cmds, &jobs, &steps);
                let mut fresh_items = tree.render();
                calculate_and_apply_diff(
                    &mut *current_items.lock().await,
                    &mut fresh_items,
                    &tree,
                    &multi_progress,
                    &main_pb,
                );

                main_pb.set_length(tree.len() as u64);
                main_pb.set_position(
                    tree.count_node_keys(|n| n.custom.payload.state != State::Progressing) as u64,
                );

                delay_for(Duration::from_millis(FETCH_DELAY_MS)).await;
            }
        }
    };

    // showing loop
    // fut3: impl Future<Output=Result<(), Error>>
    let fut3 = {
        let is_done = Arc::clone(&is_done);
        let current_items = Arc::clone(&current_items);
        async move {
            while !is_done.load(std::sync::atomic::Ordering::SeqCst) {
                for it in current_items.lock().await.iter() {
                    if it.payload.state == State::Progressing {
                        if let Some(ic) = &it.indicator {
                            ic.progress_bar.inc(1);
                        }
                    }
                }
                delay_for(Duration::from_millis(SHOW_DELAY_MS)).await;
            }
            Ok(())
        }
    };

    let (_, cmds, _) = future::try_join3(fut1, fut2, fut3).await?;
    Ok(cmds)

*/

    Ok(xs)
}

/// Waits for command completion and prints progress messages.
/// This will error on command failure and print failed commands in the error message.
pub async fn wait_for_cmds_success(cmds: &[Command]) -> Result<Vec<Command>, ImlManagerCliError> {
    let cmds = wait_for_commands(cmds).await?;

    let (failed, passed): (Vec<_>, Vec<_>) =
        cmds.into_iter().partition(|x| x.errored || x.cancelled);

    if !failed.is_empty() {
        Err(failed.into())
    } else {
        Ok(passed)
    }
}

pub async fn get_available_actions(
    id: u32,
    content_type_id: u32,
) -> Result<ApiList<AvailableAction>, ImlManagerCliError> {
    get(
        AvailableAction::endpoint_name(),
        vec![
            (
                "composite_ids",
                format!("{}:{}", content_type_id, id).as_ref(),
            ),
            ("limit", "0"),
        ],
    )
    .await
}

/// Given an `ApiList`, this fn returns the first item or errors.
pub fn first<T: EndpointName>(x: ApiList<T>) -> Result<T, ImlManagerCliError> {
    x.objects
        .into_iter()
        .next()
        .ok_or_else(|| ImlManagerCliError::DoesNotExist(T::endpoint_name()))
}

/// Wrapper for a `GET` to the Api.
pub async fn get<T: serde::de::DeserializeOwned + std::fmt::Debug>(
    endpoint: &str,
    query: impl serde::Serialize,
) -> Result<T, ImlManagerCliError> {
    let client = iml_manager_client::get_client()?;

    iml_manager_client::get(client, endpoint, query)
        .await
        .map_err(|e| e.into())
}

pub async fn graphql<T: serde::de::DeserializeOwned + std::fmt::Debug>(
    query: impl serde::Serialize + Debug,
) -> Result<T, ImlManagerCliError> {
    let client = iml_manager_client::get_client()?;

    iml_manager_client::graphql(client, query)
        .await
        .map_err(|e| e.into())
}

/// Wrapper for a `POST` to the Api.
pub async fn post(
    endpoint: &str,
    body: impl serde::Serialize,
) -> Result<iml_manager_client::Response, ImlManagerCliError> {
    let client = iml_manager_client::get_client()?;

    iml_manager_client::post(client, endpoint, body)
        .await
        .map_err(|e| e.into())
}

/// Wrapper for a `PUT` to the Api.
pub async fn put(
    endpoint: &str,
    body: impl serde::Serialize,
) -> Result<iml_manager_client::Response, ImlManagerCliError> {
    let client = iml_manager_client::get_client()?;
    iml_manager_client::put(client, endpoint, body)
        .await
        .map_err(|e| e.into())
}

/// Wrapper for a `DELETE` to the Api.
pub async fn delete(
    endpoint: &str,
    query: impl serde::Serialize,
) -> Result<iml_manager_client::Response, ImlManagerCliError> {
    let client = iml_manager_client::get_client().expect("Could not create API client");
    iml_manager_client::delete(client, endpoint, query)
        .await
        .map_err(|e| e.into())
}

pub async fn get_hosts() -> Result<ApiList<Host>, ImlManagerCliError> {
    get(Host::endpoint_name(), Host::query()).await
}

pub async fn get_all<T: EndpointName + FlatQuery + Debug + serde::de::DeserializeOwned>(
) -> Result<ApiList<T>, ImlManagerCliError> {
    get(T::endpoint_name(), T::query()).await
}

pub async fn get_one<T: EndpointName + FlatQuery + Debug + serde::de::DeserializeOwned>(
    query: Vec<(&str, &str)>,
) -> Result<T, ImlManagerCliError> {
    let mut q = T::query();
    q.extend(query);
    first(get(T::endpoint_name(), q).await?)
}

pub async fn get_influx<T: serde::de::DeserializeOwned + std::fmt::Debug>(
    db: &str,
    influxql: &str,
) -> Result<T, ImlManagerCliError> {
    let client = iml_manager_client::get_client()?;
    iml_manager_client::get_influx(client, db, influxql)
        .await
        .map_err(|e| e.into())
}

// region functions build_fresh_items / build_gen_tree
fn build_fresh_tree(
    cmd_ids: &[i32],
    commands: &HashMap<i32, RichCommand>,
    jobs: &HashMap<i32, RichJob>,
    steps: &HashMap<i32, RichStep>,
) -> Tree<TypedId, Payload> {
    let mut full_tree = Tree::new();
    for c in cmd_ids {
        let cmd = &commands[&c];
        if cmd.deps().iter().all(|j| jobs.contains_key(j)) {
            let extract_fun = |job: &Arc<Job0>| extract_wait_fors_from_job(job, &jobs);
            let jobs_graph_data = cmd
                .deps()
                .iter()
                .map(|k| RichJob::new(Arc::clone(&jobs[k].inner), extract_fun))
                .collect::<Vec<RichJob>>();
            let dag = build_direct_dag(&jobs_graph_data);
            let mut tree = build_gen_tree(cmd, &dag, &steps);
            // The collapsing is needed to reduce some deep levels of the
            // tree so that all the trees fit into terminal screens.
            // Errored nodes are leaved non-collapsed.
            let pairs = tree.keys_on_level(2);
            for (id, s) in pairs {
                if s != State::Errored || s != State::Cancelled {
                    if let Some(c) = tree.get_custom_data_mut(id) {
                        c.collapsed = true;
                        c.payload.state = s;
                    };
                }
            }
            full_tree.merge_in(tree);
        } else {
            let custom = Custom {
                collapsed: false,
                payload: Payload {
                    state: cmd_state(cmd),
                    msg: cmd.message.clone(),
                    backtrace: String::new(),
                    console: String::new(),
                    log: String::new(),
                },
            };
            full_tree.add_child_node(TypedId::Cmd(cmd.id), None, custom);
        }
    }
    full_tree
}

pub fn build_gen_tree(
    cmd: &RichCommand,
    graph: &DependencyDAG<i32, RichJob>,
    steps: &HashMap<i32, RichStep>,
) -> Tree<TypedId, Payload> {
    fn traverse(
        graph: &DependencyDAG<i32, RichJob>,
        job: Arc<RichJob>,
        steps: &HashMap<i32, RichStep>,
        parent: Option<TypedId>,
        visited: &mut HashSet<TypedId>,
        tree: &mut Tree<TypedId, Payload>,
    ) {
        let is_new = visited.insert(TypedId::Job(job.id));
        let custom = Custom {
            collapsed: false,
            payload: Payload {
                state: job_state(&job),
                msg: job.description.clone(),
                backtrace: String::new(),
                console: String::new(),
                log: String::new(),
            },
        };
        let pk = tree.add_child_node(TypedId::Job(job.id), parent, custom);
        let new_parent = Some(pk);

        // add child jobs to the tree
        if let Some(deps) = graph.links.get(&job.id()) {
            if is_new {
                for d in deps {
                    traverse(graph, Arc::clone(d), steps, new_parent, visited, tree);
                }
            }
        }
        // add steps if any
        for step_id in &job.steps {
            if let Some(step_id) = extract_uri_id::<Step>(step_id) {
                if let Some(step) = steps.get(&step_id) {
                    let custom = Custom {
                        collapsed: false,
                        payload: Payload {
                            state: step_state(step),
                            msg: step.class_name.clone(),
                            console: step.console.clone(),
                            backtrace: step.backtrace.clone(),
                            log: step.log.clone(),
                        },
                    };
                    tree.add_child_node(TypedId::Step(step_id), new_parent, custom);
                }
            }
        }
    }
    let mut tree = Tree::new();
    let p = tree.add_child_node(
        TypedId::Cmd(cmd.id),
        None,
        Custom {
            collapsed: false,
            payload: Payload {
                state: cmd_state(cmd),
                msg: cmd.message.clone(),
                backtrace: String::new(),
                console: String::new(),
                log: String::new(),
            },
        },
    );
    tree.roots = vec![p];
    let mut visited = HashSet::new();
    for r in &graph.roots {
        traverse(
            graph,
            Arc::clone(r),
            steps,
            Some(p),
            &mut visited,
            &mut tree,
        );
    }
    tree
}

pub fn calculate_and_apply_diff(
    current_items: &mut Vec<Item<TypedId, Payload, ProgressBarIndicator>>,
    fresh_items: &mut Vec<Item<TypedId, Payload, ProgressBarIndicator>>,
    tree: &Tree<TypedId, Payload>,
    multi_progress: &MultiProgress,
    main_pb: &ProgressBar,
) {
    let diff = calculate_diff(current_items, fresh_items);
    let mut error_ids_1 = Vec::new();
    let mut error_ids_2 = Vec::new();
    apply_diff(
        current_items,
        fresh_items,
        &diff,
        |i, _j, y| {
            let mut y = y.clone();
            let indi = ProgressBarIndicator {
                progress_bar: multi_progress.insert(i, ProgressBar::new(1_000_000)),
                active_style: Cell::new(None),
            };
            if y.payload.state == State::Errored || y.payload.state == State::Cancelled {
                error_ids_1.push(y.key);
            }
            set_progress_bar_message(&indi, &y);
            y.indicator = Some(indi);
            (i, y)
        },
        |i, _j, x, y| {
            let mut y = y.clone();
            if let Some(indi) = &x.indicator {
                set_progress_bar_message(indi, &y);
                if y.payload.state == State::Errored || y.payload.state == State::Cancelled {
                    error_ids_2.push(y.key);
                }
            }
            y.indicator = x.indicator.clone();
            (i, y)
        },
        |i, y| {
            if let Some(indi) = &y.indicator {
                multi_progress.remove(&indi.progress_bar);
            }
            i
        },
    );
    for eid in error_ids_1 {
        if tree.contains_key(eid) {
            print_error(&tree, eid, |s| main_pb.println(s));
        }
    }
    for eid in error_ids_2 {
        if tree.contains_key(eid) {
            print_error(&tree, eid, |s| main_pb.println(s));
        }
    }
}

fn set_progress_bar_message(
    ind: &ProgressBarIndicator,
    item: &Item<TypedId, Payload, ProgressBarIndicator>,
) {
    // two styles are applied because indicatif doesn't able to set the spinner symbol
    // after the progress bar completed.
    let sty_aux = ProgressStyle::default_bar().template("{prefix} {spinner:.green} {msg}");
    let sty_aux_finish = ProgressStyle::default_bar().template("{prefix} {msg}");

    match item.payload.state {
        State::Progressing => {
            if ind.active_style.get() != Some(true) {
                ind.progress_bar.set_style(sty_aux);
                ind.active_style.set(Some(true));
            }
            ind.progress_bar.set_prefix(&item.indent);
            ind.progress_bar.set_message(&format!("{}", item.payload));
        }
        _ => {
            if ind.active_style.get() != Some(false) {
                ind.progress_bar.set_style(sty_aux_finish);
                ind.active_style.set(Some(false));
            }
            ind.progress_bar.set_prefix(&item.indent);
            ind.progress_bar
                .set_message(&format!("{} {}", item.payload.state, item.payload));
        }
    }
}
// endregion

pub fn extract_uri_id<T: EndpointName>(input: &str) -> Option<i32> {
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

pub fn extract_children_from_cmd(cmd: &Command) -> (i32, Vec<i32>) {
    let mut deps = cmd
        .jobs
        .iter()
        .filter_map(|s| extract_uri_id::<Job0>(s))
        .collect::<Vec<i32>>();
    deps.sort();
    (cmd.id, deps)
}

pub fn extract_children_from_job(job: &Job0) -> (i32, Vec<i32>) {
    let mut deps = job
        .steps
        .iter()
        .filter_map(|s| extract_uri_id::<Step>(s))
        .collect::<Vec<i32>>();
    deps.sort();
    (job.id, deps)
}

pub fn extract_children_from_step(step: &Step) -> (i32, Vec<i32>) {
    (step.id, Vec::new()) // steps have no descendants
}

pub fn extract_wait_fors_from_job(job: &Job0, jobs: &HashMap<i32, RichJob>) -> (i32, Vec<i32>) {
    // Extract the interdependencies between jobs.
    // See [command_modal::tests::test_jobs_ordering]
    let mut deps = job
        .wait_for
        .iter()
        .filter_map(|s| extract_uri_id::<Job0>(s))
        .collect::<Vec<i32>>();
    let triple = |id: &i32| {
        jobs.get(id)
            .map(|arj| (-(arj.deps.len() as i32), &arj.description[..], arj.id))
            .unwrap_or((0, "", *id))
    };
    deps.sort_by(|i1, i2| {
        let t1 = triple(i1);
        let t2 = triple(i2);
        t1.cmp(&t2)
    });
    (job.id, deps)
}
