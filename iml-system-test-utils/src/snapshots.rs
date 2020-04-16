use crate::vagrant;
use iml_cmd::CmdError;
use petgraph::{graph::DiGraph, prelude::*, visit::EdgeFiltered};
use std::{cmp::Ordering, collections::HashMap, fmt, process::Output, str};

type SnapshotMap = HashMap<String, Vec<SnapshotName>>;

#[derive(Clone, PartialEq, Eq, Debug)]
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

#[derive(Eq, PartialEq, PartialOrd, Clone, Debug)]
pub enum SnapshotName {
    Bare,
    ImlInstalled,
    ServersDeployed,
    StratagemServersDeployed,
    LdiskfsInstalled,
    ZfsInstalled,
    StratagemInstalled,
}

impl SnapshotName {
    pub fn ordinal(&self) -> usize {
        match &*self {
            Self::Bare => 0,
            Self::ImlInstalled => 1,
            Self::ServersDeployed => 2,
            Self::StratagemServersDeployed => 3,
            Self::LdiskfsInstalled => 4,
            Self::ZfsInstalled => 5,
            Self::StratagemInstalled => 6,
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
            "bare" => Self::Bare,
            "iml-installed" => Self::ImlInstalled,
            "servers-deployed" => Self::ServersDeployed,
            "stratagem-servers-deployed" => Self::StratagemServersDeployed,
            "ldiskfs-installed" => Self::LdiskfsInstalled,
            "zfs-installed" => Self::ZfsInstalled,
            "stratagem-installed" => Self::StratagemInstalled,
            _ => Self::Bare,
        }
    }
}

impl fmt::Display for SnapshotName {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            Self::Bare => write!(f, "bare"),
            Self::ImlInstalled => write!(f, "iml-installed"),
            Self::ServersDeployed => write!(f, "servers-deployed"),
            Self::StratagemServersDeployed => write!(f, "stratagem-servers-deployed"),
            Self::LdiskfsInstalled => write!(f, "ldiskfs-installed"),
            Self::ZfsInstalled => write!(f, "zfs-installed"),
            Self::StratagemInstalled => write!(f, "stratagem-installed"),
        }
    }
}

pub fn create_graph(snapshots: Vec<SnapshotName>) -> DiGraph<Snapshot, SnapshotPath> {
    let mut graph = DiGraph::<Snapshot, SnapshotPath>::new();

    let bare = graph.add_node(Snapshot {
        name: SnapshotName::Bare,
        available: snapshots.contains(&SnapshotName::Bare),
    });
    let iml_installed = graph.add_node(Snapshot {
        name: SnapshotName::ImlInstalled,
        available: snapshots.contains(&SnapshotName::ImlInstalled),
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

    graph.extend_with_edges(&[
        (bare, iml_installed, SnapshotPath::All),
        (bare, servers_deployed, SnapshotPath::LdiskfsOrZfs),
        (bare, stratagem_servers_deployed, SnapshotPath::Stratagem),
        (iml_installed, servers_deployed, SnapshotPath::LdiskfsOrZfs),
        (
            iml_installed,
            stratagem_servers_deployed,
            SnapshotPath::Stratagem,
        ),
        (servers_deployed, ldiskfs_installed, SnapshotPath::Ldiskfs),
        (servers_deployed, zfs_installed, SnapshotPath::Zfs),
        (
            stratagem_servers_deployed,
            stratagem_installed,
            SnapshotPath::Stratagem,
        ),
    ]);

    graph
}

fn rpm_filter(snapshot: &Snapshot) -> bool {
    snapshot.available
}

fn docker_filter(snapshot: &Snapshot) -> bool {
    snapshot.available && snapshot.name != SnapshotName::ImlInstalled
}

fn get_ldiskfs_snapshots<'a>(
    graph: &'a DiGraph<Snapshot, SnapshotPath>,
    env_filter: &'a dyn Fn(&Snapshot) -> bool,
) -> Vec<&'a Snapshot> {
    let start_node = graph
        .node_indices()
        .find(|x| graph[*x].name == SnapshotName::Bare)
        .expect("Couldn't find starting node.");

    let filt = EdgeFiltered::from_fn(&graph, |e| {
        let weight = e.weight();
        weight == &SnapshotPath::All
            || weight == &SnapshotPath::Ldiskfs
            || weight == &SnapshotPath::LdiskfsOrZfs
    });

    let mut dfs = Dfs::new(&filt, start_node);
    let mut items: Vec<&Snapshot> = vec![];
    while let Some(n) = dfs.next(&filt) {
        let snapshot = &graph[n];
        if env_filter(&snapshot) {
            items.push(snapshot);
        }
    }

    items
}

fn get_zfs_snapshots<'a>(
    graph: &'a DiGraph<Snapshot, SnapshotPath>,
    env_filter: &'a dyn Fn(&Snapshot) -> bool,
) -> Vec<&'a Snapshot> {
    let start_node = graph
        .node_indices()
        .find(|x| graph[*x].name == SnapshotName::Bare)
        .expect("Couldn't find starting node.");

    let filt = EdgeFiltered::from_fn(&graph, |e| {
        let weight = e.weight();
        weight == &SnapshotPath::All
            || weight == &SnapshotPath::Zfs
            || weight == &SnapshotPath::LdiskfsOrZfs
    });

    let mut dfs = Dfs::new(&filt, start_node);
    let mut items: Vec<&Snapshot> = vec![];
    while let Some(n) = dfs.next(&filt) {
        let snapshot = &graph[n];
        if env_filter(&snapshot) {
            items.push(snapshot);
        }
    }

    items
}

fn get_stratagem_snapshots<'a>(
    graph: &'a DiGraph<Snapshot, SnapshotPath>,
    env_filter: &'a dyn Fn(&Snapshot) -> bool,
) -> Vec<&'a Snapshot> {
    let start_node = graph
        .node_indices()
        .find(|x| graph[*x].name == SnapshotName::Bare)
        .expect("Couldn't find starting node.");

    let filt = EdgeFiltered::from_fn(&graph, |e| {
        let weight = e.weight();
        weight == &SnapshotPath::All || weight == &SnapshotPath::Stratagem
    });

    let mut dfs = Dfs::new(&filt, start_node);
    let mut items: Vec<&Snapshot> = vec![];
    while let Some(n) = dfs.next(&filt) {
        let snapshot = &graph[n];
        println!("snapshot name: {}", snapshot.name);
        if env_filter(&snapshot) {
            items.push(snapshot);
        }
    }

    items
}

async fn fetch_snapshot_list() -> Result<std::process::Output, CmdError> {
    let mut cmd = vagrant::vagrant().await?;

    println!("Running source snapshot list");
    let x = cmd.arg("snapshot").arg("list").output().await?;

    Ok(x)
}

fn parse_snapshots(snapshots: Output) -> SnapshotMap {
    let (_, mut snapshot_map) = str::from_utf8(&snapshots.stdout)
        .expect("Couldn't parse snapshot list.")
        .lines()
        .fold(("", HashMap::new()), |(mut key, mut map), x| {
            if x.find("==>").is_some() {
                if x.trim().split(' ').count() == 2 {
                    key = &x[4..x.len() - 1];
                    map.insert(key.to_string(), vec![]);
                }

                (&key, map)
            } else {
                let v = map
                    .get_mut(key)
                    .unwrap_or_else(|| panic!("Couldn't find key {} in snapshot map.", key));
                v.push(SnapshotName::from(&x.to_string()));

                (&key, map)
            }
        });

    for snapshot_list in snapshot_map.values_mut() {
        snapshot_list.sort();
    }

    snapshot_map
}

pub async fn get_snapshots() -> Result<SnapshotMap, CmdError> {
    let snapshot_data = fetch_snapshot_list().await?;
    Ok(parse_snapshots(snapshot_data))
}

#[cfg(test)]
mod tests {
    use super::*;
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
iml-installed
ldiskfs-installed
stratagem-installed
stratagem-servers-deployed
zfs-installed
==> adm: VM not created. Moving on...
==> mds1:
bare
stratagem-installed
ldiskfs-installed
stratagem-servers-deployed
zfs-installed
servers-deployed
iml-installed
==> mds2:
ldiskfs-installed
zfs-installed
stratagem-installed
stratagem-servers-deployed
bare
iml-installed
servers-deployed
==> oss1:
bare
zfs-installed
servers-deployed
ldiskfs-installed
iml-installed
stratagem-installed
stratagem-servers-deployed
==> oss2:
iml-installed
bare
stratagem-servers-deployed
zfs-installed
ldiskfs-installed
servers-deployed
stratagem-installed
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

    fn get_full_graph() -> DiGraph<Snapshot, SnapshotPath> {
        create_graph(vec![
            SnapshotName::Bare,
            SnapshotName::ImlInstalled,
            SnapshotName::ServersDeployed,
            SnapshotName::StratagemServersDeployed,
            SnapshotName::LdiskfsInstalled,
            SnapshotName::ZfsInstalled,
            SnapshotName::StratagemInstalled,
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
                        SnapshotName::ImlInstalled,
                        SnapshotName::ServersDeployed,
                        SnapshotName::StratagemServersDeployed,
                        SnapshotName::LdiskfsInstalled,
                        SnapshotName::ZfsInstalled,
                        SnapshotName::StratagemInstalled,
                    ]
                ),
                (
                    "mds1".into(),
                    vec![
                        SnapshotName::Bare,
                        SnapshotName::ImlInstalled,
                        SnapshotName::ServersDeployed,
                        SnapshotName::StratagemServersDeployed,
                        SnapshotName::LdiskfsInstalled,
                        SnapshotName::ZfsInstalled,
                        SnapshotName::StratagemInstalled
                    ]
                ),
                (
                    "mds2".into(),
                    vec![
                        SnapshotName::Bare,
                        SnapshotName::ImlInstalled,
                        SnapshotName::ServersDeployed,
                        SnapshotName::StratagemServersDeployed,
                        SnapshotName::LdiskfsInstalled,
                        SnapshotName::ZfsInstalled,
                        SnapshotName::StratagemInstalled
                    ]
                ),
                (
                    "oss1".into(),
                    vec![
                        SnapshotName::Bare,
                        SnapshotName::ImlInstalled,
                        SnapshotName::ServersDeployed,
                        SnapshotName::StratagemServersDeployed,
                        SnapshotName::LdiskfsInstalled,
                        SnapshotName::ZfsInstalled,
                        SnapshotName::StratagemInstalled
                    ]
                ),
                (
                    "oss2".into(),
                    vec![
                        SnapshotName::Bare,
                        SnapshotName::ImlInstalled,
                        SnapshotName::ServersDeployed,
                        SnapshotName::StratagemServersDeployed,
                        SnapshotName::LdiskfsInstalled,
                        SnapshotName::ZfsInstalled,
                        SnapshotName::StratagemInstalled
                    ]
                ),
            ]
            .into_iter()
            .collect::<SnapshotMap>(),
            snapshots
        );
    }

    #[test]
    fn test_get_rpm_ldiskfs_snapshots_from_graph() {
        let graph = get_full_graph();

        let snapshots = get_ldiskfs_snapshots(&graph, &rpm_filter)
            .iter()
            .map(|s| &s.name)
            .collect::<Vec<&SnapshotName>>();

        assert_eq!(
            vec![
                &SnapshotName::Bare,
                &SnapshotName::ImlInstalled,
                &SnapshotName::ServersDeployed,
                &SnapshotName::LdiskfsInstalled,
            ],
            snapshots
        );
    }

    #[test]
    fn test_get_docker_ldiskfs_snapshots_from_graph() {
        let graph = get_full_graph();

        let snapshots = get_ldiskfs_snapshots(&graph, &docker_filter)
            .iter()
            .map(|s| &s.name)
            .collect::<Vec<&SnapshotName>>();

        assert_eq!(
            vec![
                &SnapshotName::Bare,
                &SnapshotName::ServersDeployed,
                &SnapshotName::LdiskfsInstalled,
            ],
            snapshots
        );
    }

    #[test]
    fn test_get_rpm_zfs_snapshots_from_graph() {
        let graph = get_full_graph();

        let snapshots = get_zfs_snapshots(&graph, &rpm_filter)
            .iter()
            .map(|s| &s.name)
            .collect::<Vec<&SnapshotName>>();

        assert_eq!(
            vec![
                &SnapshotName::Bare,
                &SnapshotName::ImlInstalled,
                &SnapshotName::ServersDeployed,
                &SnapshotName::ZfsInstalled,
            ],
            snapshots
        );
    }

    #[test]
    fn test_get_docker_zfs_snapshots_from_graph() {
        let graph = get_full_graph();

        let snapshots = get_zfs_snapshots(&graph, &docker_filter)
            .iter()
            .map(|s| &s.name)
            .collect::<Vec<&SnapshotName>>();

        assert_eq!(
            vec![
                &SnapshotName::Bare,
                &SnapshotName::ServersDeployed,
                &SnapshotName::ZfsInstalled,
            ],
            snapshots
        );
    }

    #[test]
    fn test_get_rpm_stratagem_snapshots_from_graph() {
        let graph = get_full_graph();

        let snapshots = get_stratagem_snapshots(&graph, &rpm_filter)
            .iter()
            .map(|s| &s.name)
            .collect::<Vec<&SnapshotName>>();

        assert_eq!(
            vec![
                &SnapshotName::Bare,
                &SnapshotName::ImlInstalled,
                &SnapshotName::StratagemServersDeployed,
                &SnapshotName::StratagemInstalled,
            ],
            snapshots
        );
    }

    #[test]
    fn test_get_docker_stratagem_snapshots_from_graph() {
        let graph = get_full_graph();

        let snapshots = get_stratagem_snapshots(&graph, &docker_filter)
            .iter()
            .map(|s| &s.name)
            .collect::<Vec<&SnapshotName>>();

        assert_eq!(
            vec![
                &SnapshotName::Bare,
                &SnapshotName::StratagemServersDeployed,
                &SnapshotName::StratagemInstalled,
            ],
            snapshots
        );
    }

    #[test]
    fn test_generate_graph_dot_file() {
        let graph = get_full_graph();
        let dot = Dot::with_config(&graph, &[]);
        println!("{:?}", dot);
    }
}
