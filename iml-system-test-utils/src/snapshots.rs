use crate::*;
use futures::{Future, FutureExt};
use petgraph::{
    graph::{DiGraph, EdgeIndex, NodeIndex},
    prelude::*,
    visit::EdgeFiltered,
    Direction,
};
use std::{cmp::Ordering, collections::HashMap, fmt, pin::Pin, process::Output, str};

type SnapshotMap = HashMap<String, Vec<SnapshotName>>;

type BoxedFuture = Pin<Box<dyn Future<Output = Result<Config, TestError>> + Send>>;
type TransitionFn = Box<dyn Fn(Config) -> BoxedFuture + Send + Sync>;

#[derive(PartialEq, Eq, Debug)]
pub enum SnapshotPath {
    Ldiskfs,
    Zfs,
    Stratagem,
    LdiskfsOrZfs,
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

#[derive(Eq, PartialEq, PartialOrd, Debug)]
pub enum SnapshotName {
    Init,
    Bare,
    ImlConfigured,
    ImlStratagemConfigured,
    ServersDeployed,
    StratagemServersDeployed,
    LdiskfsInstalled,
    ZfsInstalled,
    StratagemInstalled,
    LdiskfsCreated,
    ZfsCreated,
    StratagemCreated,
    FilesystemDetected,
}

impl SnapshotName {
    pub fn ordinal(&self) -> usize {
        match &*self {
            Self::Init => 0,
            Self::Bare => 1,
            Self::ImlConfigured => 2,
            Self::ImlStratagemConfigured => 3,
            Self::ServersDeployed => 4,
            Self::StratagemServersDeployed => 5,
            Self::LdiskfsInstalled => 6,
            Self::ZfsInstalled => 7,
            Self::StratagemInstalled => 8,
            Self::LdiskfsCreated => 9,
            Self::ZfsCreated => 10,
            Self::StratagemCreated => 11,
            Self::FilesystemDetected => 12,
        }
    }
}

impl Ord for SnapshotName {
    fn cmp(&self, other: &SnapshotName) -> Ordering {
        self.ordinal().cmp(&other.ordinal())
    }
}

impl From<&String> for SnapshotName {
    fn from(s: &String) -> Self {
        match s.to_lowercase().as_str() {
            "init" => Self::Init,
            "bare" => Self::Bare,
            "iml-configured" => Self::ImlConfigured,
            "iml-stratagem-configured" => Self::ImlStratagemConfigured,
            "servers-deployed" => Self::ServersDeployed,
            "stratagem-servers-deployed" => Self::StratagemServersDeployed,
            "ldiskfs-installed" => Self::LdiskfsInstalled,
            "zfs-installed" => Self::ZfsInstalled,
            "stratagem-installed" => Self::StratagemInstalled,
            "ldiskfs-created" => Self::LdiskfsCreated,
            "zfs-created" => Self::ZfsCreated,
            "stratagem-created" => Self::StratagemCreated,
            "filesystem-detected" => Self::FilesystemDetected,
            _ => Self::Bare,
        }
    }
}

impl fmt::Display for SnapshotName {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::Init => write!(f, "init"),
            Self::Bare => write!(f, "bare"),
            Self::ImlConfigured => write!(f, "iml-configured"),
            Self::ImlStratagemConfigured => write!(f, "iml-stratagem-configured"),
            Self::ServersDeployed => write!(f, "servers-deployed"),
            Self::StratagemServersDeployed => write!(f, "stratagem-servers-deployed"),
            Self::LdiskfsInstalled => write!(f, "ldiskfs-installed"),
            Self::ZfsInstalled => write!(f, "zfs-installed"),
            Self::StratagemInstalled => write!(f, "stratagem-installed"),
            Self::LdiskfsCreated => write!(f, "ldiskfs-created"),
            Self::ZfsCreated => write!(f, "zfs-created"),
            Self::StratagemCreated => write!(f, "stratagem-created"),
            Self::FilesystemDetected => write!(f, "filesystem-detected"),
        }
    }
}

pub fn get_snapshot_name_for_state(config: &Config, state: TestState) -> snapshots::SnapshotName {
    match state {
        TestState::Bare => SnapshotName::Bare,
        TestState::Configured => {
            if config.use_stratagem {
                SnapshotName::ImlStratagemConfigured
            } else {
                SnapshotName::ImlConfigured
            }
        }
        TestState::ServersDeployed => {
            if config.use_stratagem {
                SnapshotName::StratagemServersDeployed
            } else {
                SnapshotName::ServersDeployed
            }
        }
        TestState::FsInstalled => {
            if config.use_stratagem {
                SnapshotName::StratagemInstalled
            } else {
                match config.fs_type {
                    FsType::LDISKFS => SnapshotName::LdiskfsInstalled,
                    FsType::ZFS => SnapshotName::ZfsInstalled,
                }
            }
        }
        TestState::FsCreated => {
            if config.use_stratagem {
                SnapshotName::StratagemCreated
            } else {
                match config.fs_type {
                    FsType::LDISKFS => SnapshotName::LdiskfsCreated,
                    FsType::ZFS => SnapshotName::ZfsCreated,
                }
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
    let iml_configured = graph.add_node(Snapshot {
        name: SnapshotName::ImlConfigured,
        available: snapshots.contains(&SnapshotName::ImlConfigured),
    });
    let iml_stratagem_configured = graph.add_node(Snapshot {
        name: SnapshotName::ImlStratagemConfigured,
        available: snapshots.contains(&SnapshotName::ImlStratagemConfigured),
    });
    let servers_deployed = graph.add_node(Snapshot {
        name: SnapshotName::ServersDeployed,
        available: snapshots.contains(&SnapshotName::ServersDeployed),
    });
    let stratagem_servers_deployed = graph.add_node(Snapshot {
        name: SnapshotName::StratagemServersDeployed,
        available: snapshots.contains(&SnapshotName::StratagemServersDeployed),
    });
    let ldiskfs_installed = graph.add_node(Snapshot {
        name: SnapshotName::LdiskfsInstalled,
        available: snapshots.contains(&SnapshotName::LdiskfsInstalled),
    });
    let zfs_installed = graph.add_node(Snapshot {
        name: SnapshotName::ZfsInstalled,
        available: snapshots.contains(&SnapshotName::ZfsInstalled),
    });
    let stratagem_installed = graph.add_node(Snapshot {
        name: SnapshotName::StratagemInstalled,
        available: snapshots.contains(&SnapshotName::StratagemInstalled),
    });
    let ldiskfs_created = graph.add_node(Snapshot {
        name: SnapshotName::LdiskfsCreated,
        available: snapshots.contains(&SnapshotName::LdiskfsCreated),
    });
    let zfs_created = graph.add_node(Snapshot {
        name: SnapshotName::ZfsCreated,
        available: snapshots.contains(&SnapshotName::ZfsCreated),
    });
    let stratagem_created = graph.add_node(Snapshot {
        name: SnapshotName::StratagemCreated,
        available: snapshots.contains(&SnapshotName::StratagemCreated),
    });
    let filesystem_detected = graph.add_node(Snapshot {
        name: SnapshotName::FilesystemDetected,
        available: snapshots.contains(&SnapshotName::FilesystemDetected),
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
        iml_configured,
        Transition {
            path: SnapshotPath::LdiskfsOrZfs,
            transition: mk_transition(configure_iml),
        },
    );

    graph.add_edge(
        bare,
        iml_stratagem_configured,
        Transition {
            path: SnapshotPath::Stratagem,
            transition: mk_transition(configure_iml),
        },
    );

    graph.add_edge(
        iml_configured,
        servers_deployed,
        Transition {
            path: SnapshotPath::LdiskfsOrZfs,
            transition: mk_transition(deploy_servers),
        },
    );

    graph.add_edge(
        iml_stratagem_configured,
        stratagem_servers_deployed,
        Transition {
            path: SnapshotPath::Stratagem,
            transition: mk_transition(deploy_servers),
        },
    );

    graph.add_edge(
        servers_deployed,
        ldiskfs_installed,
        Transition {
            path: SnapshotPath::Ldiskfs,
            transition: mk_transition(install_fs),
        },
    );

    graph.add_edge(
        servers_deployed,
        zfs_installed,
        Transition {
            path: SnapshotPath::Zfs,
            transition: mk_transition(install_fs),
        },
    );

    graph.add_edge(
        stratagem_servers_deployed,
        stratagem_installed,
        Transition {
            path: SnapshotPath::Stratagem,
            transition: mk_transition(install_fs),
        },
    );

    graph.add_edge(
        ldiskfs_installed,
        ldiskfs_created,
        Transition {
            path: SnapshotPath::Ldiskfs,
            transition: mk_transition(create_fs),
        },
    );

    graph.add_edge(
        zfs_installed,
        zfs_created,
        Transition {
            path: SnapshotPath::Zfs,
            transition: mk_transition(create_fs),
        },
    );

    graph.add_edge(
        stratagem_installed,
        stratagem_created,
        Transition {
            path: SnapshotPath::Stratagem,
            transition: mk_transition(create_fs),
        },
    );

    graph.add_edge(
        ldiskfs_created,
        filesystem_detected,
        Transition {
            path: SnapshotPath::Ldiskfs,
            transition: mk_transition(detect_fs),
        },
    );

    graph.add_edge(
        zfs_created,
        filesystem_detected,
        Transition {
            path: SnapshotPath::ZFS,
            transition: mk_transition(detect_fs),
        },
    );

    graph.add_edge(
        stratagem_created,
        filesystem_detected,
        Transition {
            path: SnapshotPath::Stratagem,
            transition: mk_transition(detect_fs),
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
    path == &SnapshotPath::All
        || path == &SnapshotPath::LdiskfsOrZfs
        || path == &SnapshotPath::Ldiskfs
}

fn zfs_filter(path: &SnapshotPath) -> bool {
    path == &SnapshotPath::All || path == &SnapshotPath::LdiskfsOrZfs || path == &SnapshotPath::Zfs
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
        match config.fs_type {
            FsType::LDISKFS => get_snapshots_from_graph(graph, &ldiskfs_filter),
            FsType::ZFS => get_snapshots_from_graph(graph, &zfs_filter),
        }
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
        match config.fs_type {
            FsType::LDISKFS => get_test_path(graph, start_node, &ldiskfs_filter),
            FsType::ZFS => get_test_path(graph, start_node, &zfs_filter),
        }
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
                if line.find("==>").is_some() {
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
servers-deployed
iml-configured
stratagem-created
iml-stratagem-configured
ldiskfs-installed
stratagem-installed
ldiskfs-created
stratagem-servers-deployed
zfs-installed
zfs-created
==> adm: VM not created. Moving on...
==> mds1: 
bare
zfs-created
stratagem-installed
stratagem-created
ldiskfs-installed
stratagem-servers-deployed
zfs-installed
servers-deployed
ldiskfs-created
iml-stratagem-configured
iml-configured
==> mds2: 
stratagem-created
ldiskfs-installed
zfs-installed
ldiskfs-created
stratagem-installed
stratagem-servers-deployed
iml-stratagem-configured
bare
zfs-created
iml-configured
servers-deployed
==> oss1: 
bare
stratagem-created
iml-stratagem-configured
zfs-installed
ldiskfs-created
servers-deployed
ldiskfs-installed
iml-configured
zfs-created
stratagem-installed
stratagem-servers-deployed
==> oss2: 
iml-configured
bare
ldiskfs-created
stratagem-servers-deployed
zfs-installed
stratagem-created
ldiskfs-installed
zfs-created
servers-deployed
stratagem-installed
iml-stratagem-configured
==> c2: VM not created. Moving on...
==> c3: VM not created. Moving on...
==> c4: VM not created. Moving on...
==> c5: VM not created. Moving on...
==> c6: VM not created. Moving on...
==> c7: VM not created. Moving on...
==> c8: VM not created. Moving on..."#
                .as_bytes()
                .iter()
                .cloned()
                .collect(),
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
        create_graph(&vec![
            SnapshotName::Bare,
            SnapshotName::ImlConfigured,
            SnapshotName::ImlStratagemConfigured,
            SnapshotName::ServersDeployed,
            SnapshotName::StratagemServersDeployed,
            SnapshotName::LdiskfsInstalled,
            SnapshotName::ZfsInstalled,
            SnapshotName::StratagemInstalled,
            SnapshotName::LdiskfsCreated,
            SnapshotName::ZfsCreated,
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
                        SnapshotName::ImlConfigured,
                        SnapshotName::ImlStratagemConfigured,
                        SnapshotName::ServersDeployed,
                        SnapshotName::StratagemServersDeployed,
                        SnapshotName::LdiskfsInstalled,
                        SnapshotName::ZfsInstalled,
                        SnapshotName::StratagemInstalled,
                        SnapshotName::LdiskfsCreated,
                        SnapshotName::ZfsCreated,
                        SnapshotName::StratagemCreated,
                    ]
                ),
                (
                    "mds1".into(),
                    vec![
                        SnapshotName::Bare,
                        SnapshotName::ImlConfigured,
                        SnapshotName::ImlStratagemConfigured,
                        SnapshotName::ServersDeployed,
                        SnapshotName::StratagemServersDeployed,
                        SnapshotName::LdiskfsInstalled,
                        SnapshotName::ZfsInstalled,
                        SnapshotName::StratagemInstalled,
                        SnapshotName::LdiskfsCreated,
                        SnapshotName::ZfsCreated,
                        SnapshotName::StratagemCreated,
                    ]
                ),
                (
                    "mds2".into(),
                    vec![
                        SnapshotName::Bare,
                        SnapshotName::ImlConfigured,
                        SnapshotName::ImlStratagemConfigured,
                        SnapshotName::ServersDeployed,
                        SnapshotName::StratagemServersDeployed,
                        SnapshotName::LdiskfsInstalled,
                        SnapshotName::ZfsInstalled,
                        SnapshotName::StratagemInstalled,
                        SnapshotName::LdiskfsCreated,
                        SnapshotName::ZfsCreated,
                        SnapshotName::StratagemCreated,
                    ]
                ),
                (
                    "oss1".into(),
                    vec![
                        SnapshotName::Bare,
                        SnapshotName::ImlConfigured,
                        SnapshotName::ImlStratagemConfigured,
                        SnapshotName::ServersDeployed,
                        SnapshotName::StratagemServersDeployed,
                        SnapshotName::LdiskfsInstalled,
                        SnapshotName::ZfsInstalled,
                        SnapshotName::StratagemInstalled,
                        SnapshotName::LdiskfsCreated,
                        SnapshotName::ZfsCreated,
                        SnapshotName::StratagemCreated,
                    ]
                ),
                (
                    "oss2".into(),
                    vec![
                        SnapshotName::Bare,
                        SnapshotName::ImlConfigured,
                        SnapshotName::ImlStratagemConfigured,
                        SnapshotName::ServersDeployed,
                        SnapshotName::StratagemServersDeployed,
                        SnapshotName::LdiskfsInstalled,
                        SnapshotName::ZfsInstalled,
                        SnapshotName::StratagemInstalled,
                        SnapshotName::LdiskfsCreated,
                        SnapshotName::ZfsCreated,
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
                &SnapshotName::ImlConfigured,
                &SnapshotName::ServersDeployed,
                &SnapshotName::LdiskfsInstalled,
                &SnapshotName::LdiskfsCreated,
            ],
            snapshots
        );
    }

    #[test]
    fn test_get_rpm_zfs_snapshots_from_graph() {
        let graph = get_full_graph();

        let snapshots = get_snapshots_from_graph(&graph, &zfs_filter)
            .iter()
            .map(|s| &s.name)
            .collect::<Vec<&SnapshotName>>();

        assert_eq!(
            vec![
                &SnapshotName::Init,
                &SnapshotName::Bare,
                &SnapshotName::ImlConfigured,
                &SnapshotName::ServersDeployed,
                &SnapshotName::ZfsInstalled,
                &SnapshotName::ZfsCreated,
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
                &SnapshotName::ImlStratagemConfigured,
                &SnapshotName::StratagemServersDeployed,
                &SnapshotName::StratagemInstalled,
                &SnapshotName::StratagemCreated,
            ],
            snapshots
        );
    }

    #[test]
    fn test_get_ldiskfs_test_path_from_graph() {
        let graph = create_graph(&vec![]);

        let edges = get_test_path(&graph, &SnapshotName::Init, &ldiskfs_filter);

        assert_snapshot!(print_edges(&graph, &edges));
    }

    #[test]
    fn test_get_zfs_test_path_from_graph() {
        let graph = create_graph(&vec![]);

        let edges = get_test_path(&graph, &SnapshotName::Init, &zfs_filter);

        assert_snapshot!(print_edges(&graph, &edges));
    }

    #[test]
    fn test_get_stratagem_test_path_from_graph() {
        let graph = create_graph(&vec![]);

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
