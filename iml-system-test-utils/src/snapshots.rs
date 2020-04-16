use petgraph::graph::{NodeIndex, DiGraph};

pub struct Snapshot {
  pub name: SnapshotName,
  pub available: bool
}

impl Default for Snapshot {
  fn default () -> Self {
    Self {
      name: SnapshotName::None,
      available: false,
    }
  }
}

pub enum SnapshotName {
  None,
  Bare,
  ImlInstalled,
  ServersDeployed,
  StratagemServersDeployed,
  LdiskfsInstalled,
  ZfsInstalled,
  StratagemInstalled,
}

pub fn init() -> DiGraph<Snapshot, ()> {
  let mut graph = DiGraph::<Snapshot, ()>::new();

  let bare = graph.add_node(Snapshot {
    name: SnapshotName::Bare,
    available: false,
  });
  let iml_installed = graph.add_node(Snapshot {
    name: SnapshotName::ImlInstalled,
    available: false,
  });
  let servers_deployed = graph.add_node(Snapshot {
    name: SnapshotName::ServersDeployed,
    available: false,
  });
  let stratagem_servers_deployed = graph.add_node(Snapshot {
    name: SnapshotName::ServersDeployed,
    available: false,
  });
  let ldiskfs_installed = graph.add_node(Snapshot {
    name: SnapshotName::LdiskfsInstalled,
    available: false,
  });
  let zfs_installed = graph.add_node(Snapshot {
    name: SnapshotName::ZfsInstalled,
    available: false,
  });
  let stratagem_installed = graph.add_node(Snapshot {
    name: SnapshotName::StratagemInstalled,
    available: false,
  });

  graph.extend_with_edges(&[
    (bare, iml_installed)
    (iml_installed, servers_deployed, TestType::Ldiskfs), (iml_installed, servers_deployed, TestType::Zfs), (iml_installed, servers_deployed, TestType::Stratagem),
    (servers_deployed, filesystem_installed, TestType::Ldiskfs), (servers_deployed, filesystem_installed, TestType::Zfs), (servers_deployed, filesystem_installed, TestType::Stratagem)
  ]);

  graph
}
