use crate::*;
use futures::{Future, FutureExt};
use petgraph::{
    graph::{DiGraph, EdgeIndex, NodeIndex},
    prelude::*,
    visit::EdgeFiltered,
    Direction,
};
use std::{collections::HashMap, fmt, pin::Pin, process::Output, str};

type SnapshotMap = HashMap<String, Vec<SnapshotName>>;

type BoxedFuture = Pin<Box<dyn Future<Output = Result<Config, TestError>> + Send>>;
type TransitionFn = Box<dyn Fn(Config) -> BoxedFuture + Send + Sync>;

#[derive(PartialEq, Eq, Debug)]
pub enum SnapshotPath {
    Ldiskfs,
    Stratagem,
    All,
}

#[derive(Debug)]
pub struct Snapshot {
    pub name: SnapshotName,
    pub available: bool,
}

impl Default for Snapshot {
    fn default() -> Self {
        Self {
            name: SnapshotName::Bare,
            available: false,
        }
    }
}

pub struct Transition {
    path: SnapshotPath,
    pub transition: TransitionFn,
}

impl<'a> fmt::Debug for Transition {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(format!("{:?}", self.path).as_str())
    }
}

#[derive(Eq, PartialEq, PartialOrd, Ord, Debug, Copy, Clone)]
#[repr(usize)]
pub enum SnapshotName {
    Init,
    Bare,
    LustreRpmsInstalled,
    ImlConfigured,
    ServersDeployed,
    LdiskfsCreated,
    StratagemCreated,
    LdiskfsDetected,
    StratagemDetected,
    StratagemMountedClient,
    StratagemTestTaskQueue,
}

impl From<&String> for SnapshotName {
    fn from(s: &String) -> Self {
        match s.to_lowercase().as_str() {
            "init" => Self::Init,
            "bare" => Self::Bare,
            "lustre-rpms-installed" => Self::LustreRpmsInstalled,
            "iml-configured" => Self::ImlConfigured,
            "servers-deployed" => Self::ServersDeployed,
            "ldiskfs-created" => Self::LdiskfsCreated,
            "stratagem-created" => Self::StratagemCreated,
            "ldiskfs-detected" => Self::LdiskfsDetected,
            "stratagem-detected" => Self::StratagemDetected,
            "stratagem-mounted-client" => Self::StratagemMountedClient,
            "stratagem-test-taskqueue" => Self::StratagemTestTaskQueue,
            _ => Self::Bare,
        }
    }
}

impl fmt::Display for SnapshotName {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::Init => write!(f, "init"),
            Self::Bare => write!(f, "bare"),
            Self::LustreRpmsInstalled => write!(f, "lustre-rpms-installed"),
            Self::ImlConfigured => write!(f, "iml-configured"),
            Self::ServersDeployed => write!(f, "servers-deployed"),
            Self::LdiskfsCreated => write!(f, "ldiskfs-created"),
            Self::StratagemCreated => write!(f, "stratagem-created"),
            Self::LdiskfsDetected => write!(f, "ldiskfs-detected"),
            Self::StratagemDetected => write!(f, "stratagem-detected"),
            Self::StratagemMountedClient => write!(f, "stratagem-mounted-client"),
            Self::StratagemTestTaskQueue => write!(f, "stratagem-test-taskqueue"),
        }
    }
}

pub fn get_snapshot_name_for_state(config: &Config, state: TestState) -> snapshots::SnapshotName {
    match state {
        TestState::Bare => SnapshotName::Bare,
        TestState::LustreRpmsInstalled => SnapshotName::LustreRpmsInstalled,
        TestState::Configured => SnapshotName::ImlConfigured,
        TestState::ServersDeployed => SnapshotName::ServersDeployed,
        TestState::FsCreated => {
            if config.use_stratagem {
                SnapshotName::StratagemCreated
            } else {
                SnapshotName::LdiskfsCreated
            }
        }
    }
}

fn mk_transition<Fut>(f: fn(Config) -> Fut) -> TransitionFn
where
    Fut: Future<Output = Result<Config, TestError>> + Send + 'static,
{
    Box::new(move |config| Box::pin(f(config).boxed()))
}

pub fn create_graph(snapshots: &[SnapshotName]) -> DiGraph<Snapshot, Transition> {
    let mut graph = DiGraph::<Snapshot, Transition>::new();

    let init = graph.add_node(Snapshot {
        name: SnapshotName::Init,
        available: true,
    });
    let bare = graph.add_node(Snapshot {
        name: SnapshotName::Bare,
        available: snapshots.contains(&SnapshotName::Bare),
    });
    let lustre_rpms_installed = graph.add_node(Snapshot {
        name: SnapshotName::LustreRpmsInstalled,
        available: snapshots.contains(&SnapshotName::LustreRpmsInstalled),
    });
    let iml_configured = graph.add_node(Snapshot {
        name: SnapshotName::ImlConfigured,
        available: snapshots.contains(&SnapshotName::ImlConfigured),
    });
    let servers_deployed = graph.add_node(Snapshot {
        name: SnapshotName::ServersDeployed,
        available: snapshots.contains(&SnapshotName::ServersDeployed),
    });
    let ldiskfs_created = graph.add_node(Snapshot {
        name: SnapshotName::LdiskfsCreated,
        available: snapshots.contains(&SnapshotName::LdiskfsCreated),
    });
    let stratagem_created = graph.add_node(Snapshot {
        name: SnapshotName::StratagemCreated,
        available: snapshots.contains(&SnapshotName::StratagemCreated),
    });
    let ldiskfs_detected = graph.add_node(Snapshot {
        name: SnapshotName::LdiskfsDetected,
        available: snapshots.contains(&SnapshotName::LdiskfsDetected),
    });
    let stratagem_detected = graph.add_node(Snapshot {
        name: SnapshotName::StratagemDetected,
        available: snapshots.contains(&SnapshotName::StratagemDetected),
    });
    let stratagem_mounted_client = graph.add_node(Snapshot {
        name: SnapshotName::StratagemMountedClient,
        available: snapshots.contains(&SnapshotName::StratagemMountedClient),
    });
    let stratagem_test_taskqueue = graph.add_node(Snapshot {
        name: SnapshotName::StratagemTestTaskQueue,
        available: snapshots.contains(&SnapshotName::StratagemTestTaskQueue),
    });

    graph.add_edge(
        init,
        bare,
        Transition {
            path: SnapshotPath::All,
            transition: mk_transition(setup_bare),
        },
    );

    graph.add_edge(
        bare,
        lustre_rpms_installed,
        Transition {
            path: SnapshotPath::All,
            transition: mk_transition(install_fs),
        },
    );

    graph.add_edge(
        lustre_rpms_installed,
        iml_configured,
        Transition {
            path: SnapshotPath::All,
            transition: mk_transition(configure_iml),
        },
    );

    graph.add_edge(
        iml_configured,
        servers_deployed,
        Transition {
            path: SnapshotPath::All,
            transition: mk_transition(deploy_servers),
        },
    );

    graph.add_edge(
        servers_deployed,
        ldiskfs_created,
        Transition {
            path: SnapshotPath::Ldiskfs,
            transition: mk_transition(create_fs),
        },
    );

    graph.add_edge(
        servers_deployed,
        stratagem_created,
        Transition {
            path: SnapshotPath::Stratagem,
            transition: mk_transition(create_fs),
        },
    );

    graph.add_edge(
        ldiskfs_created,
        ldiskfs_detected,
        Transition {
            path: SnapshotPath::Ldiskfs,
            transition: mk_transition(detect_fs),
        },
    );

    graph.add_edge(
        stratagem_created,
        stratagem_detected,
        Transition {
            path: SnapshotPath::Stratagem,
            transition: mk_transition(detect_fs),
        },
    );

    graph.add_edge(
        stratagem_detected,
        stratagem_mounted_client,
        Transition {
            path: SnapshotPath::Stratagem,
            transition: mk_transition(mount_clients),
        },
    );

    graph.add_edge(
        stratagem_mounted_client,
        stratagem_test_taskqueue,
        Transition {
            path: SnapshotPath::Stratagem,
            transition: mk_transition(test_stratagem_taskqueue),
        },
    );

    graph
}

fn get_node_by_name(graph: &DiGraph<Snapshot, Transition>, name: &SnapshotName) -> NodeIndex {
    graph
        .node_indices()
        .find(|x| graph[*x].name == *name)
        .unwrap_or_else(|| panic!("Couldn't find node {} in graph.", name))
}

fn ldiskfs_filter(path: &SnapshotPath) -> bool {
    path == &SnapshotPath::All || path == &SnapshotPath::Ldiskfs
}

fn stratagem_filter(path: &SnapshotPath) -> bool {
    path == &SnapshotPath::All || path == &SnapshotPath::Stratagem
}

fn get_snapshots_from_graph<'a>(
    graph: &'a DiGraph<Snapshot, Transition>,
    filter: &dyn Fn(&SnapshotPath) -> bool,
) -> Vec<&'a Snapshot> {
    let start_node = get_node_by_name(&graph, &SnapshotName::Init);

    let filt = EdgeFiltered::from_fn(&graph, |e| {
        let weight = e.weight();
        filter(&weight.path)
    });

    let mut dfs = Dfs::new(&filt, start_node);
    let mut items: Vec<&Snapshot> = vec![];
    while let Some(n) = dfs.next(&filt) {
        let snapshot = &graph[n];
        if snapshot.available {
            items.push(snapshot);
        }
    }

    items
}

fn get_test_path<'a>(
    graph: &'a DiGraph<Snapshot, Transition>,
    start_node: &SnapshotName,
    filter: &dyn Fn(&SnapshotPath) -> bool,
) -> Vec<EdgeIndex> {
    let mut edges = vec![];
    let node = get_node_by_name(&graph, start_node);

    let filtered_graph = EdgeFiltered::from_fn(&graph, |e| {
        let weight = e.weight();
        filter(&weight.path)
    });

    let mut dfs = Dfs::new(&filtered_graph, node);

    while let Some(node) = dfs.next(&graph) {
        let mut neighbor_edges = graph.neighbors_directed(node, Direction::Outgoing).detach();

        while let Some(edge) = neighbor_edges.next_edge(&graph) {
            let path = &graph[edge].path;

            if filter(path) {
                edges.push(edge);
                break;
            }
        }
    }

    edges
}

pub fn get_active_snapshots<'a>(
    config: &'a Config,
    graph: &'a DiGraph<Snapshot, Transition>,
) -> Vec<&'a Snapshot> {
    if config.use_stratagem {
        get_snapshots_from_graph(graph, &stratagem_filter)
    } else {
        get_snapshots_from_graph(graph, &ldiskfs_filter)
    }
}

pub fn get_active_test_path(
    config: &Config,
    graph: &DiGraph<Snapshot, Transition>,
    start_node: &SnapshotName,
) -> Vec<EdgeIndex> {
    if config.use_stratagem {
        get_test_path(graph, start_node, &stratagem_filter)
    } else {
        get_test_path(graph, start_node, &ldiskfs_filter)
    }
}

pub async fn fetch_snapshot_list() -> Result<std::process::Output, TestError> {
    let mut cmd = vagrant::vagrant().await?;

    let x = cmd.arg("snapshot").arg("list").output().await?;

    Ok(x)
}

pub fn parse_snapshots(snapshots: Output) -> SnapshotMap {
    let (_, mut snapshot_map) = str::from_utf8(&snapshots.stdout)
        .expect("Couldn't parse snapshot list.")
        .lines()
        .fold(
            (
                "",
                vec![
                    ("iscsi".to_string(), vec![]),
                    ("mds1".to_string(), vec![]),
                    ("mds2".to_string(), vec![]),
                    ("oss1".to_string(), vec![]),
                    ("oss2".to_string(), vec![]),
                ]
                .into_iter()
                .collect::<HashMap<String, Vec<SnapshotName>>>(),
            ),
            |(mut key, mut map), x| {
                let line = x.trim();
                if line.contains("==>") {
                    if line.split(' ').count() == 2 {
                        key = &line[4..line.len() - 1];
                        map.insert(key.to_string(), vec![]);
                    }

                    (&key, map)
                } else if !key.is_empty() {
                    let v = map
                        .get_mut(key)
                        .unwrap_or_else(|| panic!("Couldn't find key {} in snapshot map.", key));

                    v.push(SnapshotName::from(&line.to_string()));

                    (&key, map)
                } else {
                    (&key, map)
                }
            },
        );

    for snapshot_list in snapshot_map.values_mut() {
        snapshot_list.sort();
    }

    snapshot_map
}

pub async fn get_snapshots() -> Result<SnapshotMap, TestError> {
    let snapshot_data = fetch_snapshot_list().await?;
    Ok(parse_snapshots(snapshot_data))
}

#[cfg(test)]
mod tests {
    use super::*;
    use insta::assert_snapshot;
    use petgraph::dot::Dot;
    use std::os::unix::process::ExitStatusExt;
    use std::process::ExitStatus;

    fn get_snapshot_output() -> Output {
        Output {
            status: ExitStatus::from_raw(0),
            stderr: vec![],
            stdout: r#"==> iscsi: 
bare
lustre-rpms-installed
servers-deployed
iml-configured
stratagem-created
ldiskfs-created
==> adm: VM not created. Moving on...
==> mds1: 
bare
lustre-rpms-installed
stratagem-created
servers-deployed
ldiskfs-created
iml-configured
==> mds2: 
stratagem-created
ldiskfs-created
lustre-rpms-installed
bare
iml-configured
servers-deployed
==> oss1: 
bare
lustre-rpms-installed
stratagem-created
ldiskfs-created
servers-deployed
iml-configured
==> oss2: 
iml-configured
bare
lustre-rpms-installed
ldiskfs-created
stratagem-created
servers-deployed
==> c2: VM not created. Moving on...
==> c3: VM not created. Moving on...
==> c4: VM not created. Moving on...
==> c5: VM not created. Moving on...
==> c6: VM not created. Moving on...
==> c7: VM not created. Moving on...
==> c8: VM not created. Moving on..."#
                .as_bytes()
                .to_vec(),
        }
    }

    fn print_edges(graph: &DiGraph<Snapshot, Transition>, edges: &[EdgeIndex]) -> String {
        let mut edge_info: String = "".into();
        for edge in edges {
            let nodes = graph.edge_endpoints(*edge).unwrap();
            let snapshots = (&graph[nodes.0], &graph[nodes.1]);
            edge_info = format!(
                "{}edge: {:?} has nodes {:?}\n",
                edge_info, graph[*edge], snapshots
            );
        }

        edge_info
    }

    fn get_full_graph() -> DiGraph<Snapshot, Transition> {
        create_graph(&[
            SnapshotName::Bare,
            SnapshotName::LustreRpmsInstalled,
            SnapshotName::ImlConfigured,
            SnapshotName::ServersDeployed,
            SnapshotName::LdiskfsCreated,
            SnapshotName::StratagemCreated,
        ])
    }

    #[test]
    fn test_get_snapshots() {
        let snapshots = parse_snapshots(get_snapshot_output());

        assert_eq!(
            vec![
                (
                    "iscsi".into(),
                    vec![
                        SnapshotName::Bare,
                        SnapshotName::LustreRpmsInstalled,
                        SnapshotName::ImlConfigured,
                        SnapshotName::ServersDeployed,
                        SnapshotName::LdiskfsCreated,
                        SnapshotName::StratagemCreated,
                    ]
                ),
                (
                    "mds1".into(),
                    vec![
                        SnapshotName::Bare,
                        SnapshotName::LustreRpmsInstalled,
                        SnapshotName::ImlConfigured,
                        SnapshotName::ServersDeployed,
                        SnapshotName::LdiskfsCreated,
                        SnapshotName::StratagemCreated,
                    ]
                ),
                (
                    "mds2".into(),
                    vec![
                        SnapshotName::Bare,
                        SnapshotName::LustreRpmsInstalled,
                        SnapshotName::ImlConfigured,
                        SnapshotName::ServersDeployed,
                        SnapshotName::LdiskfsCreated,
                        SnapshotName::StratagemCreated,
                    ]
                ),
                (
                    "oss1".into(),
                    vec![
                        SnapshotName::Bare,
                        SnapshotName::LustreRpmsInstalled,
                        SnapshotName::ImlConfigured,
                        SnapshotName::ServersDeployed,
                        SnapshotName::LdiskfsCreated,
                        SnapshotName::StratagemCreated,
                    ]
                ),
                (
                    "oss2".into(),
                    vec![
                        SnapshotName::Bare,
                        SnapshotName::LustreRpmsInstalled,
                        SnapshotName::ImlConfigured,
                        SnapshotName::ServersDeployed,
                        SnapshotName::LdiskfsCreated,
                        SnapshotName::StratagemCreated,
                    ]
                ),
            ]
            .into_iter()
            .collect::<SnapshotMap>(),
            snapshots
        );
    }

    #[test]
    fn test_get_ldiskfs_snapshots_from_graph() {
        let graph = get_full_graph();

        let snapshots = get_snapshots_from_graph(&graph, &ldiskfs_filter)
            .iter()
            .map(|s| &s.name)
            .collect::<Vec<&SnapshotName>>();

        assert_eq!(
            vec![
                &SnapshotName::Init,
                &SnapshotName::Bare,
                &SnapshotName::LustreRpmsInstalled,
                &SnapshotName::ImlConfigured,
                &SnapshotName::ServersDeployed,
                &SnapshotName::LdiskfsCreated,
            ],
            snapshots
        );
    }

    #[test]
    fn test_get_rpm_stratagem_snapshots_from_graph() {
        let graph = get_full_graph();

        let snapshots = get_snapshots_from_graph(&graph, &stratagem_filter)
            .iter()
            .map(|s| &s.name)
            .collect::<Vec<&SnapshotName>>();

        assert_eq!(
            vec![
                &SnapshotName::Init,
                &SnapshotName::Bare,
                &SnapshotName::LustreRpmsInstalled,
                &SnapshotName::ImlConfigured,
                &SnapshotName::ServersDeployed,
                &SnapshotName::StratagemCreated,
            ],
            snapshots
        );
    }

    #[test]
    fn test_get_ldiskfs_test_path_from_graph() {
        let graph = create_graph(&[]);

        let edges = get_test_path(&graph, &SnapshotName::Init, &ldiskfs_filter);

        assert_snapshot!(print_edges(&graph, &edges));
    }

    #[test]
    fn test_get_stratagem_test_path_from_graph() {
        let graph = create_graph(&[]);

        let edges = get_test_path(&graph, &SnapshotName::Init, &stratagem_filter);

        assert_snapshot!(print_edges(&graph, &edges));
    }

    #[test]
    fn test_generate_graph_dot_file() {
        let graph = get_full_graph();
        let dot = Dot::with_config(&graph, &[]);
        println!("graph {:?}", dot);
    }
}
