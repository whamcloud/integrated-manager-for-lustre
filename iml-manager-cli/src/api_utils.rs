// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::diff::{calculate_diff, AlignmentOp, Keyed, Side};
use crate::{display_utils, error::ImlManagerCliError};
use futures::{future, FutureExt, TryFutureExt};
use iml_api_utils::dependency_tree::{build_direct_dag, traverse_graph, Deps, Rich};
use iml_wire_types::{ApiList, AvailableAction, Command, EndpointName, FlatQuery, Host, Job, Step};
use indicatif::{MultiProgress, ProgressBar, ProgressStyle};
use regex::{Captures, Regex};
use std::sync::Arc;
use std::{collections::HashMap, fmt::Debug, iter, time::Duration};
use tokio::task::JoinError;
use tokio::{task::spawn_blocking, time::delay_for};

type Job0 = Job<Option<serde_json::Value>>;
type RichCommand = Rich<i32, Command>;
type RichJob = Rich<i32, Job0>;
type RichStep = Rich<i32, Step>;

#[derive(Copy, Clone, Hash, PartialEq, Eq, Ord, PartialOrd, Debug)]
pub struct CmdId(i32);

#[derive(Copy, Clone, Hash, PartialEq, Eq, Ord, PartialOrd, Debug)]
pub struct JobId(i32);

#[derive(Copy, Clone, Hash, PartialEq, Eq, Debug)]
pub enum TypedId {
    Command(i32),
    Job(i32),
    Step(i32),
}

#[derive(Debug, Clone)]
struct Context<'a> {
    level: usize,
    steps: &'a HashMap<i32, RichStep>,
}

#[derive(Debug, Clone)]
pub struct ProgressLine {
    the_id: TypedId,
    indent: usize,
    msg: String,
    progress_bar: Option<ProgressBar>,
}

impl PartialEq for ProgressLine {
    fn eq(&self, other: &Self) -> bool {
        self.the_id == other.the_id && self.indent == other.indent && self.msg == other.msg
    }
}

impl Eq for ProgressLine {}

impl Keyed for ProgressLine {
    type Key = TypedId;
    fn key(&self) -> Self::Key {
        self.the_id
    }
}

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

fn cmd_finished(cmd: &Command) -> bool {
    cmd.complete
}

fn job_finished<T>(job: &Job<T>) -> bool {
    // job.state can be "pending", "tasked" or "complete"
    // if a job is errored or cancelled, it is also complete
    job.state == "complete"
}

fn step_finished(step: &Step) -> bool {
    // step.state can be "success", "failed" or "incomplete"
    step.state != "incomplete"
}

pub async fn wait_for_cmd(cmd: Command) -> Result<Command, ImlManagerCliError> {
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
pub async fn wait_for_commands(cmds: &[Command]) -> Result<Vec<Command>, ImlManagerCliError> {
    let multi_progress_0 = Arc::new(MultiProgress::new());
    let spinner_style = ProgressStyle::default_spinner()
        .tick_chars("⠁⠂⠄⡀⢀⠠⠐⠈ ")
        .template("{prefix:.bold.dim} {spinner} {wide_msg}");

    // current_xs mirrors the multi progress bar
    let mut current_lines: Vec<ProgressLine> = vec![];

    let mut commands: HashMap<i32, RichCommand> = HashMap::new();
    let mut jobs: HashMap<i32, RichJob> = HashMap::new();
    let mut steps: HashMap<i32, RichStep> = HashMap::new();

    let mut cmd_ids = vec![];

    for cmd in cmds.iter() {
        let (id, deps) = extract_children_from_cmd(cmd);
        let inner = cmd.clone();
        commands.insert(id, Rich { id, deps, inner });
        cmd_ids.push(id);
    }

    for (cmd_no, c) in cmd_ids.iter().enumerate() {
        let pb = multi_progress_0.add(ProgressBar::new(100_000));
        pb.set_style(spinner_style.clone());
        pb.set_prefix(&format!("[{}/{}]", cmd_no + 1, commands.len()));
        pb.set_message(&display_utils::format_cmd_state(0, &commands[&c]));
        current_lines.push(ProgressLine {
            the_id: TypedId::Command(*c),
            indent: 0,
            msg: "".to_string(),
            progress_bar: Some(pb),
        });
    }

    let multi_progress_1 = Arc::clone(&multi_progress_0);

    let fut1 = spawn_blocking(move || multi_progress_1.join()).map(
        |r: Result<Result<(), std::io::Error>, JoinError>| {
            r.map_err(|e: JoinError| e.into())
                .and_then(std::convert::identity)
        },
    );

    let fut2 = async {
        loop {
            if commands.values().all(|cmd| cmd_finished(cmd)) {
                tracing::debug!("All commands complete. Returning");
                return Ok::<_, ImlManagerCliError>(());
            }

            fetch_and_update(&mut commands, &mut jobs, &mut steps).await?;

            let mut fresh_lines = build_fresh_lines(&cmd_ids, &commands, &jobs, &steps);
            let diff = calculate_diff(&current_lines, &fresh_lines);

            let mut cmd_no = 0;
            let mut di = 0;
            let mut dj = 0;
            for op in diff {
                match op {
                    AlignmentOp::Insert(Side::Left, i, j) => {
                        let mut x = fresh_lines[j + dj].clone();
                        if !current_lines.contains(&x) {
                            let pb = multi_progress_0.insert(i + di, ProgressBar::new(100_000));
                            pb.set_style(spinner_style.clone());
                            match x.the_id {
                                TypedId::Command(_) => {
                                    cmd_no += 1usize;
                                    pb.set_prefix(&format!("[{}/{}]", cmd_no, commands.len()));
                                }
                                TypedId::Job(_) => pb.set_prefix("     "),
                                TypedId::Step(_) => pb.set_prefix("     "),
                            };
                            pb.set_message(&format!("{}  {}", "  ".repeat(x.indent), x.msg));
                            pb.tick();
                            x.progress_bar = Some(pb);
                            current_lines.insert(i + di, x);
                            di += 1;
                        }
                    }
                    AlignmentOp::Insert(Side::Right, i, j) => {
                        // update loaded to preserve the indices to be correct
                        let x = current_lines[i + di].clone();
                        fresh_lines.insert(j + dj, x);
                        dj += 1;
                    }
                    AlignmentOp::Delete(Side::Left, i) => {
                        current_lines.remove(i + di);
                        di -= 1;
                    }
                    AlignmentOp::Delete(Side::Right, j) => {
                        // update loaded to preserve the indices to be correct
                        fresh_lines.remove(j + dj);
                        dj -= 1;
                    }
                    AlignmentOp::Replace(Side::Left, i, j) => {
                        current_lines[i + di].the_id = fresh_lines[j + dj].the_id;
                        current_lines[i + di].indent = fresh_lines[j + dj].indent;
                        current_lines[i + di].msg = fresh_lines[j + dj].msg.clone();
                        let x = &current_lines[i + di];
                        if let Some(progress_bar) = &x.progress_bar {
                            progress_bar.inc(1);
                            progress_bar.set_message(&format!(
                                "{}{}",
                                "  ".repeat(x.indent),
                                x.msg
                            ));
                        }
                    }
                    AlignmentOp::Replace(Side::Right, _, _) => {
                        // loaded_xs[j + dj] = current_xs[i + di].clone();
                    }
                }
            }
            for x in current_lines.iter_mut() {
                if let Some(pb) = &x.progress_bar {
                    let msg_opt = match x.the_id {
                        TypedId::Command(id) => commands
                            .get(&id)
                            .filter(|c| cmd_finished(c))
                            .map(|c| display_utils::format_cmd_state(x.indent, c)),
                        TypedId::Job(id) => jobs
                            .get(&id)
                            .filter(|j| job_finished(j))
                            .map(|j| display_utils::format_job_state(x.indent, j)),
                        TypedId::Step(id) => steps
                            .get(&id)
                            .filter(|s| step_finished(s))
                            .map(|s| display_utils::format_step_state(x.indent, s)),
                    };
                    if let Some(msg) = msg_opt {
                        pb.finish_with_message(&msg);
                        x.progress_bar = None;
                    } else {
                        pb.inc(1);
                    }
                }
            }
            delay_for(Duration::from_millis(500)).await;
        }
    };

    future::try_join(fut1.err_into(), fut2).await?;

    // return the commands, that
    let mut result: Vec<Command> = Vec::with_capacity(commands.len());
    for id in cmd_ids {
        if let Some(cmd) = commands.remove(&id) {
            result.push(cmd.inner)
        }
    }
    Ok(result)
}

fn build_fresh_lines(
    cmd_ids: &[i32],
    commands: &HashMap<i32, RichCommand>,
    jobs: &HashMap<i32, RichJob>,
    steps: &HashMap<i32, RichStep>,
) -> Vec<ProgressLine> {
    let mut rows = Vec::new();
    for c in cmd_ids {
        let cmd = &commands[&c];
        rows.push(ProgressLine {
            the_id: TypedId::Command(*c),
            indent: 0,
            msg: cmd.message.clone(),
            progress_bar: None,
        });
        if cmd.deps().iter().all(|j| jobs.contains_key(j)) {
            let extract_fun = |job: &Job0| extract_wait_fors_from_job(job, &jobs);
            let jobs_graph_data = cmd
                .deps()
                .iter()
                .map(|k| RichJob::new(jobs[k].inner.clone(), extract_fun))
                .collect::<Vec<RichJob>>();
            let dag = build_direct_dag(&jobs_graph_data);
            let mut ctx = Context {
                level: 0,
                steps: &steps,
            };
            let xs = traverse_graph(&dag, &rich_job_to_line, &rich_job_combine_lines, &mut ctx)
                .into_iter()
                .flatten()
                .collect::<Vec<_>>();
            for x in xs.into_iter() {
                rows.push(x);
            }
        }
    }
    rows
}

async fn fetch_and_update(
    commands: &mut HashMap<i32, RichCommand>,
    jobs: &mut HashMap<i32, RichJob>,
    steps: &mut HashMap<i32, RichStep>,
) -> Result<(), ImlManagerCliError> {
    let (load_cmd_ids, load_job_ids, load_step_ids) = extract_ids_to_load(&commands, &jobs, &steps);
    let loaded_cmds: ApiList<Command> = fetch_api_list(load_cmd_ids).await?;
    let loaded_jobs: ApiList<Job0> = fetch_api_list(load_job_ids).await?;
    let loaded_steps: ApiList<Step> = fetch_api_list(load_step_ids).await?;
    update_commands(commands, loaded_cmds.objects);
    update_jobs(jobs, loaded_jobs.objects);
    update_steps(steps, loaded_steps.objects);
    Ok(())
}

fn update_commands(commands: &mut HashMap<i32, RichCommand>, loaded_cmds: Vec<Command>) {
    let new_commands = loaded_cmds
        .into_iter()
        .map(|t| {
            let (id, deps) = extract_children_from_cmd(&t);
            (id, Rich { id, deps, inner: t })
        })
        .collect::<HashMap<i32, RichCommand>>();
    commands.extend(new_commands);
}

fn update_jobs(jobs: &mut HashMap<i32, RichJob>, loaded_jobs: Vec<Job0>) {
    let new_jobs = loaded_jobs
        .into_iter()
        .map(|t| {
            let (id, deps) = extract_children_from_job(&t);
            (id, Rich { id, deps, inner: t })
        })
        .collect::<HashMap<i32, RichJob>>();
    jobs.extend(new_jobs);
}

fn update_steps(steps: &mut HashMap<i32, RichStep>, loaded_steps: Vec<Step>) {
    let new_steps = loaded_steps
        .into_iter()
        .map(|t| {
            let (id, deps) = extract_children_from_step(&t);
            (id, Rich { id, deps, inner: t })
        })
        .collect::<HashMap<i32, RichStep>>();
    steps.extend(new_steps);
}

fn extract_ids_to_load(
    commands: &HashMap<i32, RichCommand>,
    jobs: &HashMap<i32, RichJob>,
    steps: &HashMap<i32, RichStep>,
) -> (Vec<i32>, Vec<i32>, Vec<i32>) {
    let load_cmd_ids = extract_sorted_keys(&commands)
        .into_iter()
        .filter(|c| {
            commands
                .get(c)
                .map(|cmd| !cmd_finished(cmd))
                .unwrap_or(true)
        })
        .collect::<Vec<i32>>();
    let load_job_ids = load_cmd_ids
        .iter()
        .filter(|c| commands.contains_key(c))
        .flat_map(|c| commands[c].deps())
        .filter(|j| jobs.get(j).map(|job| !job_finished(job)).unwrap_or(true))
        .copied()
        .collect::<Vec<i32>>();
    let load_step_ids = load_job_ids
        .iter()
        .filter(|j| jobs.contains_key(j))
        .flat_map(|j| jobs[j].deps())
        .filter(|s| {
            steps
                .get(s)
                .map(|step| !step_finished(step))
                .unwrap_or(true)
        })
        .copied()
        .collect::<Vec<i32>>();
    (load_cmd_ids, load_job_ids, load_step_ids)
}

fn rich_job_to_line(node: Arc<RichJob>, is_new: bool, ctx: &mut Context) -> Vec<ProgressLine> {
    ctx.level += 1;
    if is_new {
        let steps = ctx.steps;
        let mut rows = vec![ProgressLine {
            indent: ctx.level,
            the_id: TypedId::Job(node.id),
            msg: node.description.clone(),
            progress_bar: None,
        }];
        for step_id in &node.steps {
            if let Some(step_id) = extract_uri_id::<Step>(step_id) {
                if let Some(step) = steps.get(&step_id) {
                    rows.push(ProgressLine {
                        the_id: TypedId::Step(step_id),
                        indent: ctx.level + 1,
                        msg: step.class_name.clone(),
                        progress_bar: None,
                    });
                }
            }
        }
        rows
    } else {
        vec![]
    }
}

fn rich_job_combine_lines(
    node: Vec<ProgressLine>,
    nodes: Vec<Vec<ProgressLine>>,
    ctx: &mut Context,
) -> Vec<ProgressLine> {
    if ctx.level > 0 {
        ctx.level -= 1;
    }
    let mut result = Vec::with_capacity(100);
    for n in node {
        result.push(n);
    }
    for node in nodes.into_iter() {
        for n in node {
            let indent = n.indent + if ctx.level > 0 { 1 } else { 0 };
            result.push(ProgressLine {
                indent,
                the_id: n.the_id,
                msg: n.msg,
                progress_bar: None,
            })
        }
    }
    result
}

fn extract_sorted_keys<T>(hm: &HashMap<i32, T>) -> Vec<i32> {
    let mut ids = hm.keys().copied().collect::<Vec<_>>();
    ids.sort();
    ids
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

fn extract_children_from_cmd(cmd: &Command) -> (i32, Vec<i32>) {
    let mut deps = cmd
        .jobs
        .iter()
        .filter_map(|s| extract_uri_id::<Job0>(s))
        .collect::<Vec<i32>>();
    deps.sort();
    (cmd.id, deps)
}

fn extract_children_from_job(job: &Job0) -> (i32, Vec<i32>) {
    let mut deps = job
        .steps
        .iter()
        .filter_map(|s| extract_uri_id::<Step>(s))
        .collect::<Vec<i32>>();
    deps.sort();
    (job.id, deps)
}

fn extract_children_from_step(step: &Step) -> (i32, Vec<i32>) {
    (step.id, Vec::new()) // steps have no descendants
}

fn extract_wait_fors_from_job(job: &Job0, jobs: &HashMap<i32, RichJob>) -> (i32, Vec<i32>) {
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
