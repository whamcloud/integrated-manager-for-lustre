// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

use crate::{
    input_document::{client_mount, filesystem, host, lnet, mdt, mgt, mgt_mdt, ost},
    ValidateAddon,
};
use emf_wire_types::ComponentType;
use maplit::{btreemap, btreeset, hashmap, hashset};
use once_cell::sync::Lazy;
use std::{
    collections::{BTreeMap, BTreeSet, HashMap, HashSet},
    fmt,
};
use validator::{Validate, ValidationErrors};

pub(crate) static STATE_SCHEMA: Lazy<Schema> = Lazy::new(|| Schema {
    version: 1,
    components: btreemap! {
           ComponentType::Host => Component {
               states: hashmap! {
                    State::Host(host::State::Up) => None,
                    State::Host(host::State::Down) => None,
               },
               actions: hashmap! {
                   ActionName::Host(host::ActionName::SshCommand) => Action {
                       provisional: true,
                       state: None
                   },
                   ActionName::Host(host::ActionName::SetupPlanesSsh) => Action {
                       provisional: true,
                       state: None
                   },
                   ActionName::Host(host::ActionName::SyncFileSsh) => Action {
                       provisional: true,
                       state: None
                   },
               }
           },
           ComponentType::Lnet => Component {
               states: hashmap! {
                State::Lnet(lnet::State::Up) => None,
                State::Lnet(lnet::State::Down) => None,
                State::Lnet(lnet::State::Loaded) => None,
                State::Lnet(lnet::State::Unloaded) => None,
                State::Lnet(lnet::State::Configured) => None,
               },
                actions: hashmap! {
                    ActionName::Lnet(lnet::ActionName::Start) => Action {
                        state: Some(ActionState {
                            start: Some(hashset![State::Lnet(lnet::State::Down)]),
                            end: State::Lnet(lnet::State::Up)
                        }),
                        provisional: false
                    },
                    ActionName::Lnet(lnet::ActionName::Stop) => Action {
                        state: Some(ActionState {
                            start: Some(hashset![State::Lnet(lnet::State::Up)]),
                            end: State::Lnet(lnet::State::Down)
                        }),
                        provisional: false
                    },
                    ActionName::Lnet(lnet::ActionName::Load) => Action {
                        state: Some(ActionState {
                            start: Some(hashset![State::Lnet(lnet::State::Unloaded), State::Lnet(lnet::State::Up)]),
                            end: State::Lnet(lnet::State::Loaded)
                        }),
                        provisional: false
                    },
                    ActionName::Lnet(lnet::ActionName::Unload) => Action {
                        state: Some(ActionState {
                            start: Some(hashset![State::Lnet(lnet::State::Loaded)]),
                            end: State::Lnet(lnet::State::Unloaded)
                        }),
                        provisional: false
                    },
                    ActionName::Lnet(lnet::ActionName::Configure) => Action {
                        state: Some(ActionState {
                            start: Some(hashset![State::Lnet(lnet::State::Loaded)]),
                            end: State::Lnet(lnet::State::Configured)
                        }),
                        provisional: true
                    },
                    ActionName::Lnet(lnet::ActionName::Export) => Action {
                        state: Some(ActionState {
                            start: Some(hashset![State::Lnet(lnet::State::Configured)]),
                            end: State::Lnet(lnet::State::Up)
                        }),
                        provisional: false
                    },
                    ActionName::Lnet(lnet::ActionName::Unconfigure) => Action {
                        state: Some(ActionState {
                            start: Some(hashset![State::Lnet(lnet::State::Configured)]),
                            end: State::Lnet(lnet::State::Loaded)
                        }),
                        provisional: false
                    },
                    ActionName::Lnet(lnet::ActionName::Import) => Action {
                        state: Some(ActionState {
                            start: None,
                            end: State::Lnet(lnet::State::Unloaded)
                        }),
                        provisional: false
                    },
                }
           },
           ComponentType::ClientMount => Component {
               states: hashmap! {
                   State::ClientMount(client_mount::State::Mounted) => None,
                   State::ClientMount(client_mount::State::Unmounted) => None,
               },
               actions: hashmap! {
                   ActionName::ClientMount(client_mount::ActionName::Create) => Action {
                       state: Some(ActionState {
                           start: None,
                           end: State::ClientMount(client_mount::State::Mounted)
                       }),
                       provisional: true,
                   }
               }
           },
           ComponentType::Mgt => Component {
            states: hashmap! {
                State::Mgt(mgt::State::Mounted) => Some(ComponentState {
                    dependencies: Some(vec![Dependency::Exactly(DepNode{
                        name: ComponentType::Lnet,
                        state: State::Lnet(lnet::State::Up),
                    })])
                }),
                State::Mgt(mgt::State::Unmounted) => None,
            },
            actions: hashmap! {
                ActionName::Mgt(mgt::ActionName::Format) => Action {
                    state: Some(ActionState {
                        start: None,
                        end: State::Mgt(mgt::State::Unmounted)
                    }),
                    provisional: true,
                },
                ActionName::Mgt(mgt::ActionName::Mount) => Action {
                    state: Some(ActionState {
                        start: Some(hashset![State::Mgt(mgt::State::Unmounted)]),
                        end: State::Mgt(mgt::State::Mounted)
                    }),
                    provisional: false,
                },
                ActionName::Mgt(mgt::ActionName::Unmount) => Action {
                    state: Some(ActionState {
                        start: Some(hashset![State::Mgt(mgt::State::Mounted)]),
                        end: State::Mgt(mgt::State::Unmounted)
                    }),
                    provisional: false,
                }
            }
        },
        ComponentType::MgtMdt => Component {
            states: hashmap! {
                State::MgtMdt(mgt_mdt::State::Mounted) => Some(ComponentState {
                    dependencies: Some(vec![Dependency::Exactly(DepNode{
                        name: ComponentType::Lnet,
                        state: State::Lnet(lnet::State::Up),
                    })])
                }),
                State::MgtMdt(mgt_mdt::State::Unmounted) => None,
            },
            actions: hashmap! {
                ActionName::MgtMdt(mgt_mdt::ActionName::Format) => Action {
                    state: Some(ActionState {
                        start: None,
                        end: State::MgtMdt(mgt_mdt::State::Unmounted)
                    }),
                    provisional: true,
                },
                ActionName::MgtMdt(mgt_mdt::ActionName::Mount) => Action {
                    state: Some(ActionState {
                        start: Some(hashset![State::MgtMdt(mgt_mdt::State::Unmounted)]),
                        end: State::MgtMdt(mgt_mdt::State::Mounted)
                    }),
                    provisional: false,
                },
                ActionName::MgtMdt(mgt_mdt::ActionName::Unmount) => Action {
                    state: Some(ActionState {
                        start: Some(hashset![State::MgtMdt(mgt_mdt::State::Mounted)]),
                        end: State::MgtMdt(mgt_mdt::State::Unmounted)
                    }),
                    provisional: false,
                }
            }
        },
        ComponentType::Mdt => Component {
            states: hashmap! {
                State::Mdt(mdt::State::Mounted) => Some(ComponentState {
                    dependencies: Some(vec![Dependency::Exactly(DepNode{
                        name: ComponentType::Lnet,
                        state: State::Lnet(lnet::State::Up),
                    })])
                }),
                State::Mdt(mdt::State::Unmounted) => None,
            },
            actions: hashmap! {
                ActionName::Mdt(mdt::ActionName::Format) => Action {
                    state: Some(ActionState {
                        start: None,
                        end: State::Mdt(mdt::State::Unmounted)
                    }),
                    provisional: true,
                },
                ActionName::Mdt(mdt::ActionName::Mount) => Action {
                    state: Some(ActionState {
                        start: Some(hashset![State::Mdt(mdt::State::Unmounted)]),
                        end: State::Mdt(mdt::State::Mounted)
                    }),
                    provisional: false,
                },
                ActionName::Mdt(mdt::ActionName::Unmount) => Action {
                    state: Some(ActionState {
                        start: Some(hashset![State::Mdt(mdt::State::Mounted)]),
                        end: State::Mdt(mdt::State::Unmounted)
                    }),
                    provisional: false,
                }
            }
        },
        ComponentType::Ost => Component {
            states: hashmap! {
                State::Ost(ost::State::Mounted) => Some(ComponentState {
                    dependencies: Some(vec![Dependency::Exactly(DepNode{
                        name: ComponentType::Lnet,
                        state: State::Lnet(lnet::State::Up),
                    })])
                }),
                State::Ost(ost::State::Unmounted) => None,
            },
            actions: hashmap! {
                ActionName::Ost(ost::ActionName::Format) => Action {
                    state: Some(ActionState {
                        start: None,
                        end: State::Ost(ost::State::Unmounted)
                    }),
                    provisional: true,
                },
                ActionName::Ost(ost::ActionName::Mount) => Action {
                    state: Some(ActionState {
                        start: Some(hashset![State::Ost(ost::State::Unmounted)]),
                        end: State::Ost(ost::State::Mounted)
                    }),
                    provisional: false,
                },
                ActionName::Ost(ost::ActionName::Unmount) => Action {
                    state: Some(ActionState {
                        start: Some(hashset![State::Ost(ost::State::Mounted)]),
                        end: State::Ost(ost::State::Unmounted)
                    }),
                    provisional: false,
                }
            }
        },
        ComponentType::Filesystem => Component {
            states: hashmap! {
                State::Filesystem(filesystem::State::Started) => Some(ComponentState {
                    dependencies: Some(
                        vec![
                            Dependency::Or(
                                btreeset![
                                    DepNode{
                                        name: ComponentType::Mgt,
                                        state: State::Mgt(mgt::State::Mounted),
                                    },
                                    DepNode {
                                        name: ComponentType::MgtMdt,
                                        state: State::MgtMdt(mgt_mdt::State::Mounted),
                                    }
                                ]
                            ),
                            Dependency::All(
                                btreeset! [DepNode {
                                    name: ComponentType::Mdt,
                                    state: State::Mdt(mdt::State::Mounted)
                                }]
                            ),
                            Dependency::All(
                                btreeset![DepNode {
                                    name: ComponentType::Ost,
                                    state: State::Ost(ost::State::Mounted)
                                }]
                            )
                        ]
                    )
                }),
                State::Filesystem(filesystem::State::Unavailable) => None,
                State::Filesystem(filesystem::State::Available) => None,
                State::Filesystem(filesystem::State::Stopped) => None,
            },
            actions: hashmap! {
                ActionName::Filesystem(filesystem::ActionName::Start) => Action {
                    state: Some(ActionState {
                        start: Some(hashset![State::Filesystem(filesystem::State::Stopped), State::Filesystem(filesystem::State::Unavailable)]),
                        end: State::Filesystem(filesystem::State::Started)
                    }),
                    provisional: false,
                },
                ActionName::Filesystem(filesystem::ActionName::Stop) => Action {
                    state: Some(ActionState {
                        start: Some(hashset![State::Filesystem(filesystem::State::Available)]),
                        end: State::Filesystem(filesystem::State::Stopped)
                    }),
                    provisional: false,
                },
                ActionName::Filesystem(filesystem::ActionName::Create) => Action {
                    state: Some(ActionState {
                        start: None,
                        end: State::Filesystem(filesystem::State::Stopped)
                    }),
                    provisional: true,
                }
            }
        },
    },
});

#[derive(serde::Serialize, serde::Deserialize)]
#[serde(rename_all = "snake_case")]
#[serde(untagged)]
pub enum Input {
    Host(host::Input),
    Lnet(lnet::Input),
    ClientMount(client_mount::Input),
    Mgt(mgt::Input),
    MgtMdt(mgt_mdt::Input),
    Mdt(mdt::Input),
    Ost(ost::Input),
    Filesystem(filesystem::Input),
}

impl ValidateAddon for Input {
    fn validate(&self) -> Result<(), ValidationErrors> {
        match self {
            Self::Host(host::Input::SshCommand(x)) => x.validate()?,
            Self::Host(host::Input::SetupPlanesSsh(x)) => x.validate()?,
            Self::Host(host::Input::SyncFileSsh(x)) => x.validate()?,
            Self::Host(host::Input::CreateFileSsh(x)) => x.validate()?,
            Self::Lnet(lnet::Input::Configure(x)) => x.validate()?,
            Self::Lnet(lnet::Input::Export(x)) => x.validate()?,
            Self::Lnet(lnet::Input::Import(x)) => x.validate()?,
            Self::Lnet(lnet::Input::Load(x)) => x.validate()?,
            Self::Lnet(lnet::Input::Start(x)) => x.validate()?,
            Self::Lnet(lnet::Input::Stop(x)) => x.validate()?,
            Self::Lnet(lnet::Input::Unconfigure(x)) => x.validate()?,
            Self::Lnet(lnet::Input::Unload(x)) => x.validate()?,
            Self::ClientMount(client_mount::Input::Create(x)) => x.validate()?,
            Self::ClientMount(client_mount::Input::Mount(x)) => x.validate()?,
            Self::ClientMount(client_mount::Input::Unmount(x)) => x.validate()?,
            Self::Mgt(mgt::Input::Format(x)) => x.validate()?,
            Self::Mgt(mgt::Input::Mount(x)) => x.validate()?,
            Self::Mgt(mgt::Input::Unmount(x)) => x.validate()?,
            Self::MgtMdt(mgt_mdt::Input::Format(x)) => x.validate()?,
            Self::MgtMdt(mgt_mdt::Input::Mount(x)) => x.validate()?,
            Self::MgtMdt(mgt_mdt::Input::Unmount(x)) => x.validate()?,
            Self::Mdt(mdt::Input::Format(x)) => x.validate()?,
            Self::Mdt(mdt::Input::Mount(x)) => x.validate()?,
            Self::Mdt(mdt::Input::Unmount(x)) => x.validate()?,
            Self::Ost(ost::Input::Format(x)) => x.validate()?,
            Self::Ost(ost::Input::Mount(x)) => x.validate()?,
            Self::Ost(ost::Input::Unmount(x)) => x.validate()?,
            Self::Filesystem(filesystem::Input::Create(x)) => x.validate()?,
            Self::Filesystem(filesystem::Input::Start(x)) => x.validate()?,
            Self::Filesystem(filesystem::Input::Stop(x)) => x.validate()?,
        }

        Ok(())
    }
}

#[derive(
    Clone, Copy, Debug, Ord, PartialOrd, Eq, PartialEq, Hash, serde::Serialize, serde::Deserialize,
)]
#[serde(rename_all = "snake_case")]
pub enum ActionName {
    Host(host::ActionName),
    Lnet(lnet::ActionName),
    ClientMount(client_mount::ActionName),
    Mgt(mgt::ActionName),
    MgtMdt(mgt_mdt::ActionName),
    Mdt(mdt::ActionName),
    Ost(ost::ActionName),
    Filesystem(filesystem::ActionName),
}

impl fmt::Display for ActionName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        let x = match self {
            Self::Host(x) => x.to_string(),
            Self::Lnet(x) => x.to_string(),
            Self::ClientMount(x) => x.to_string(),
            Self::Mgt(x) => x.to_string(),
            Self::MgtMdt(x) => x.to_string(),
            Self::Mdt(x) => x.to_string(),
            Self::Ost(x) => x.to_string(),
            Self::Filesystem(x) => x.to_string(),
        };

        write!(f, "{}", x)
    }
}

#[derive(
    Clone, Copy, Debug, Eq, PartialEq, PartialOrd, Hash, Ord, serde::Serialize, serde::Deserialize,
)]
pub(crate) enum State {
    Host(host::State),
    Lnet(lnet::State),
    ClientMount(client_mount::State),
    Mgt(mgt::State),
    MgtMdt(mgt_mdt::State),
    Mdt(mdt::State),
    Ost(ost::State),
    Filesystem(filesystem::State),
}

#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub(crate) struct ActionState {
    #[serde(default)]
    pub start: Option<HashSet<State>>,
    pub end: State,
}

#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub(crate) struct Action {
    #[serde(default)]
    pub provisional: bool,
    pub state: Option<ActionState>,
}

#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub(crate) struct Schema {
    /// The version of the state schema
    pub version: u16,
    /// Components that can be loaded into the state machine.
    pub components: BTreeMap<ComponentType, Component>,
}

#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub(crate) struct Component {
    /// Valid states for the object.
    pub states: HashMap<State, Option<ComponentState>>,
    /// Actions available to the component.
    pub actions: HashMap<ActionName, Action>,
}

#[derive(Debug, serde::Deserialize, serde::Serialize)]
pub(crate) struct ComponentState {
    /// Dependency requirements for the state.
    #[serde(default)]
    pub dependencies: Option<Vec<Dependency>>,
}

#[derive(Clone, Debug, serde::Deserialize, Eq, Ord, PartialEq, PartialOrd, serde::Serialize)]
pub(crate) struct DepNode {
    pub name: ComponentType,
    pub state: State,
}

#[derive(Clone, Debug, serde::Deserialize, Eq, Ord, PartialEq, PartialOrd, serde::Serialize)]
#[serde(rename_all = "lowercase")]
pub(crate) enum Dependency {
    /// A list of deps that can be used with the Or qualifier. The input supplied must match one of the items.
    Or(BTreeSet<DepNode>),
    /// A list of deps that can be used with the All qualifier. The corresponding input must be a list in which all items in the list are in the specified state.
    All(BTreeSet<DepNode>),
    Exactly(DepNode),
}
