// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

pub mod client_mount;
pub mod filesystem;
pub mod host;
pub mod lnet;
pub mod mdt;
pub mod mgt;
pub mod mgt_mdt;
pub mod ost;

use crate::{
    state_schema::{ActionName, Input, STATE_SCHEMA},
    ValidateAddon as _,
};
use emf_wire_types::ComponentType;
use serde::{
    de::{self, DeserializeSeed, IntoDeserializer, MapAccess, Visitor},
    Deserialize, Deserializer,
};
pub use ssh_opts::*;
use std::{
    collections::{BTreeSet, HashMap},
    convert::TryFrom,
    fmt, io,
    time::Duration,
};
use validator::Validate;

impl<'de> Deserialize<'de> for Step {
    fn deserialize<D>(deserializer: D) -> Result<Step, D::Error>
    where
        D: Deserializer<'de>,
    {
        struct StepVisitor;

        impl<'de> Visitor<'de> for StepVisitor {
            type Value = Step;

            fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
                formatter.write_str("A well formed Step")
            }

            fn visit_map<V>(self, mut map: V) -> Result<Step, V::Error>
            where
                V: MapAccess<'de>,
            {
                let mut action = None;
                let mut id = None;
                let mut inputs = None;
                let mut outputs = None;

                while let Some(key) = map.next_key()? {
                    match key {
                        Field::Action => {
                            action = Some(map.next_value()?);
                        }
                        Field::Id => {
                            id = Some(map.next_value()?);
                        }
                        Field::Inputs => {
                            let action = match action {
                                None => return Err(de::Error::custom(
                                    "action field not found. action must be present before inputs",
                                )),
                                Some(x) => x,
                            };

                            inputs = Some(map.next_value_seed(StepPairSeed(action))?);
                        }
                        Field::Outputs => {
                            outputs = map.next_value()?;
                        }
                    }
                }

                let action = action.ok_or_else(|| de::Error::missing_field("action"))?;
                let id = id.ok_or_else(|| de::Error::missing_field("id"))?;
                let inputs = inputs.ok_or_else(|| de::Error::missing_field("inputs"))?;

                Ok(Step {
                    action,
                    id,
                    inputs,
                    outputs,
                })
            }
        }

        struct StepPairSeed(StepPair);

        impl<'de> DeserializeSeed<'de> for StepPairSeed {
            type Value = Input;

            fn deserialize<D>(self, deserializer: D) -> Result<Self::Value, D::Error>
            where
                D: Deserializer<'de>,
            {
                let input = match self.0 {
                    StepPair(ComponentType::Host, ActionName::Host(action)) => {
                        host::get_input(action, deserializer).map(Input::Host)
                    }
                    StepPair(ComponentType::Lnet, ActionName::Lnet(action)) => {
                        lnet::get_input(action, deserializer).map(Input::Lnet)
                    }
                    StepPair(ComponentType::ClientMount, ActionName::ClientMount(action)) => {
                        client_mount::get_input(action, deserializer).map(Input::ClientMount)
                    }
                    StepPair(ComponentType::Mgt, ActionName::Mgt(action)) => {
                        mgt::get_input(action, deserializer).map(Input::Mgt)
                    }
                    StepPair(ComponentType::MgtMdt, ActionName::MgtMdt(action)) => {
                        mgt_mdt::get_input(action, deserializer).map(Input::MgtMdt)
                    }
                    StepPair(ComponentType::Mdt, ActionName::Mdt(action)) => {
                        mdt::get_input(action, deserializer).map(Input::Mdt)
                    }
                    StepPair(ComponentType::Ost, ActionName::Ost(action)) => {
                        ost::get_input(action, deserializer).map(Input::Ost)
                    }
                    StepPair(ComponentType::Filesystem, ActionName::Filesystem(action)) => {
                        filesystem::get_input(action, deserializer).map(Input::Filesystem)
                    }
                    _ => todo!(),
                }?;

                Ok(input)
            }
        }

        #[derive(Deserialize)]
        #[serde(field_identifier, rename_all = "lowercase")]
        enum Field {
            Action,
            Id,
            Inputs,
            Outputs,
        }

        const FIELDS: &[&str] = &["action", "id", "inputs", "outputs"];
        deserializer.deserialize_struct("Step", FIELDS, StepVisitor)
    }
}

#[derive(Debug, thiserror::Error)]
pub struct InputDocumentErrors(Vec<InputDocumentError>);

impl From<InputDocumentError> for InputDocumentErrors {
    fn from(err: InputDocumentError) -> Self {
        Self(vec![err])
    }
}

impl fmt::Display for InputDocumentErrors {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        let s = self
            .0
            .iter()
            .map(|x| match x {
                InputDocumentError::ValidationErrors(errs) => {
                    format!("{:?}", errs)
                }
                InputDocumentError::SerdeYamlError(err) => format!("{}", err),
                InputDocumentError::SerdeYamlPathToError(err) => {
                    format!("{}", err)
                }
            })
            .collect::<Vec<String>>()
            .join("\n");

        write!(f, "{}", s)
    }
}

#[derive(thiserror::Error, Debug)]
pub enum InputDocumentError {
    #[error(transparent)]
    SerdeYamlPathToError(#[from] serde_path_to_error::Error<serde_yaml::Error>),
    #[error(transparent)]
    SerdeYamlError(#[from] serde_yaml::Error),
    #[error(transparent)]
    ValidationErrors(#[from] validator::ValidationErrors),
}

#[derive(serde::Serialize, serde::Deserialize, Validate)]
#[serde(default)]
pub struct InputDocument {
    /// The version of this input document
    pub version: f32,
    /// Jobs to submit to the state-machine.
    #[validate]
    pub jobs: HashMap<String, Job>,
    /// Whether the state-machine should execute this input document or return the changes that would be made if it did. Defaults to true.
    pub dry_run: bool,
    /// How long this input document should wait for completion before aborting. Defaults to no timeout.
    #[serde(with = "humantime_serde")]
    pub timeout: Option<Duration>,
    /// Whether the relevant components should be refreshed before executing the input document. Defaults to false.
    pub refresh: bool,
}

impl Default for InputDocument {
    fn default() -> Self {
        Self {
            version: 1.0,
            jobs: HashMap::default(),
            dry_run: true,
            timeout: None,
            refresh: false,
        }
    }
}

#[derive(serde::Serialize, serde::Deserialize, Validate)]
pub struct Job {
    /// The name to display for this job.
    #[validate(length(min = 1))]
    pub name: String,
    /// A list of jobs that must be completed before this job can run.
    #[serde(default)]
    pub needs: BTreeSet<String>,
    /// A list of steps to submit to the state-machine for this job. Each step will run sequentially
    #[validate]
    #[validate(length(min = 1))]
    pub steps: Vec<Step>,
}

#[derive(serde::Serialize, Validate)]
pub struct Step {
    /// The action to be run from the registry in `component.action` format.
    pub action: StepPair,
    /// The step identifier.
    #[validate(length(min = 1))]
    pub id: String,
    /// The input to supply to this step.
    #[serde(default)]
    #[validate]
    pub inputs: Input,
    /// Output that will be used in a future job when building the graph.
    pub outputs: Option<HashMap<String, serde_json::Value>>,
}

impl fmt::Display for Step {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Step {}", self.id)
    }
}

#[derive(Clone, Copy, Eq, PartialEq, Hash, serde::Serialize, serde::Deserialize)]
#[serde(try_from = "String")]
#[serde(into = "String")]
pub struct StepPair(ComponentType, ActionName);

impl StepPair {
    pub fn new(component: ComponentType, action: ActionName) -> Self {
        Self(component, action)
    }
}

impl TryFrom<String> for StepPair {
    type Error = io::Error;

    fn try_from(s: String) -> Result<Self, Self::Error> {
        let xs: Vec<_> = s.split('.').map(|x| x.trim()).collect();

        let (component_name, action) = match xs.as_slice() {
            [component_name, action] => (component_name, action),
            _ => {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidInput,
                    format!(
                        "Action specification {} invalid. Must be specified as 'component.action'",
                        s
                    ),
                ));
            }
        };

        let component_type = match serde_json::from_str(&format!("\"{}\"", component_name)) {
            Ok(x) => x,
            _ => {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidInput,
                    format!("Component {} is unknown.", component_name),
                ));
            }
        };

        if !STATE_SCHEMA.components.contains_key(&component_type) {
            return Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                format!("Component {} is unknown.", component_name),
            ));
        }

        let action = match component_type {
            ComponentType::Host => host::ActionName::try_from(*action).map(ActionName::Host)?,
            ComponentType::Lnet => lnet::ActionName::try_from(*action).map(ActionName::Lnet)?,
            ComponentType::ClientMount => {
                client_mount::ActionName::try_from(*action).map(ActionName::ClientMount)?
            }
            ComponentType::Mgt => mgt::ActionName::try_from(*action).map(ActionName::Mgt)?,
            ComponentType::MgtMdt => {
                mgt_mdt::ActionName::try_from(*action).map(ActionName::MgtMdt)?
            }
            ComponentType::Mdt => mdt::ActionName::try_from(*action).map(ActionName::Mdt)?,
            ComponentType::Ost => ost::ActionName::try_from(*action).map(ActionName::Ost)?,
            ComponentType::Filesystem => {
                filesystem::ActionName::try_from(*action).map(ActionName::Filesystem)?
            }
            ComponentType::Target => todo!(),
            ComponentType::Ntp => todo!(),
        };

        Ok(StepPair(component_type, action))
    }
}

impl From<StepPair> for String {
    fn from(p: StepPair) -> Self {
        format!("{}.{}", p.0.to_string(), p.1.to_string())
    }
}

#[derive(Clone, Copy, serde::Serialize, serde::Deserialize, Validate)]
#[serde(try_from = "serde_json::Value")]
#[serde(deny_unknown_fields)]
pub struct NullInput;

impl TryFrom<serde_json::Value> for NullInput {
    type Error = io::Error;

    fn try_from(s: serde_json::Value) -> Result<Self, Self::Error> {
        if s.is_null() {
            Ok(Self)
        } else {
            Err(io::Error::new(
                io::ErrorKind::InvalidInput,
                "Expected no input.",
            ))
        }
    }
}

fn deserialize_input<'a, 'de, D, T>(input: D) -> Result<T, D::Error>
where
    T: serde::Deserialize<'de> + Validate,
    D: Deserializer<'de>,
{
    let x = T::deserialize(input)?;

    Ok(x)
}

/// Deserializes an input document string and returns an `InputDocument` structure if successful.
pub fn deserialize_input_document(
    document: impl AsRef<[u8]>,
) -> Result<InputDocument, InputDocumentErrors> {
    let val: serde_yaml::Value =
        serde_yaml::from_slice(document.as_ref()).map_err(InputDocumentError::SerdeYamlError)?;
    let des = val.into_deserializer();

    let input_doc: InputDocument =
        serde_path_to_error::deserialize(des).map_err(InputDocumentError::SerdeYamlPathToError)?;

    input_doc
        .validate()
        .map_err(InputDocumentError::ValidationErrors)?;

    Ok(input_doc)
}

pub mod ssh_opts {
    use validator::{Validate, ValidationError};

    fn default_port() -> u16 {
        22
    }

    fn default_user() -> String {
        "root".to_string()
    }

    #[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
    pub struct SshProxyOpts {
        pub host: String,
        /// SSH port
        #[serde(default = "default_port")]
        pub port: u16,
        /// SSH user
        #[serde(default = "default_user")]
        pub user: String,
        /// SSH password. If empty, key auth will be used
        #[serde(default)]
        pub password: Option<String>,
    }

    #[cfg(feature = "ssh-conversions")]
    impl From<&SshProxyOpts> for emf_ssh::ProxyCfg {
        fn from(cfg: &SshProxyOpts) -> Self {
            let auth = if let Some(pw) = cfg.password.as_ref() {
                emf_ssh::ProxyAuth::Password(pw.to_string())
            } else {
                emf_ssh::ProxyAuth::Key
            };

            Self {
                host: cfg.host.to_string(),
                user: cfg.user.to_string(),
                port: Some(cfg.port),
                auth,
            }
        }
    }

    #[derive(Debug, serde::Serialize, serde::Deserialize, Validate)]
    #[serde(default)]
    pub struct SshOpts {
        /// SSH port
        pub port: u16,
        /// SSH user
        pub user: String,
        #[validate(custom(function = "validate_auth"))]
        pub auth_opts: AuthOpts,
        pub proxy_opts: Option<SshProxyOpts>,
    }

    impl Default for SshOpts {
        fn default() -> Self {
            Self {
                port: 22,
                user: "root".to_string(),
                proxy_opts: None,
                auth_opts: AuthOpts {
                    agent: false,
                    password: None,
                    key_path: None,
                    key_passphrase: None,
                },
            }
        }
    }

    #[derive(Debug, serde::Serialize, serde::Deserialize)]

    pub struct AuthOpts {
        /// Use ssh-agent to authenticate
        #[serde(default)]
        pub agent: bool,
        /// Use password authentication
        pub password: Option<String>,
        /// Use private key authentication
        pub key_path: Option<String>,
        /// Private key passphrase
        pub key_passphrase: Option<String>,
    }

    #[cfg(feature = "ssh-conversions")]
    impl From<&AuthOpts> for emf_ssh::Auth {
        fn from(opts: &AuthOpts) -> Self {
            if opts.agent {
                Self::Agent
            } else if let Some(pw) = &opts.password {
                Self::Password(pw.to_string())
            } else if let Some(key_path) = &opts.key_path {
                Self::Key {
                    key_path: key_path.to_string(),
                    password: opts.key_passphrase.as_ref().map(|x| x.to_string()),
                }
            } else {
                Self::Auto
            }
        }
    }

    fn validate_auth(auth: &AuthOpts) -> Result<(), ValidationError> {
        if auth.agent
            && auth
                .key_path
                .as_ref()
                .or(auth.key_passphrase.as_ref())
                .or(auth.password.as_ref())
                .is_some()
        {
            return Err(ValidationError::new(
                "ssh-agent auth cannot be used with key or password auth",
            ));
        }

        if auth
            .password
            .as_ref()
            .and(auth.key_path.as_ref().or(auth.key_passphrase.as_ref()))
            .is_some()
        {
            return Err(ValidationError::new(
                "SSH password auth cannot be used with key-based auth",
            ));
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn invalid_input_document() -> Result<(), InputDocumentErrors> {
        let s = r#"
version: 1
jobs:
    add_mds1:
        name: Add Mds1
        steps:
            - action: host.ssh_command
              inputs:
                  host: mds1
                  run: touch test
              outputs:
                  id: this.id
    configure_lnet:
        name: configure lnet
        needs:
            - add_mds1
        steps:
            - action: lnet.configure
              id: step1
              inputs:
                  path: /dev/sfa/sda1
                  host_id: '${{needs.add_mds1.step1.outputs.id}}'
timeout: 5 minutes
"#;

        let errs = deserialize_input_document(s).err().unwrap();

        insta::assert_display_snapshot!(errs);

        Ok(())
    }

    #[test]
    fn valid_input_document() -> Result<(), InputDocumentErrors> {
        let s = r#"
version: 1
jobs:
  add_mds1:
    name: Add Mds1
    steps:
      - action: host.ssh_command
        id: step1
        inputs:
          host: mds1
          run: touch test
          ssh_opts:
            port: 22
            user: root
            proxy_opts:
              host: proxy-host
        outputs:
          id: this.id
  configure_lnet:
    name: configure lnet
    needs:
      - add_mds1
    steps:
      - action: lnet.configure
        inputs:
          network: tcp0
          ethernet: eth1
          host: "${{needs.add_mds1.step1.outputs.id}}"
        id: step1
        outputs:
timeout: 5 minutes"#
            .trim();

        let doc = deserialize_input_document(s)?;

        insta::with_settings!({sort_maps => true}, {
            insta::assert_yaml_snapshot!(doc);
        });

        Ok(())
    }

    #[test]
    fn round_trip_input_document() -> Result<(), Box<dyn std::error::Error>> {
        let s = r#"
version: 1
jobs:
  add_mds1:
    name: Add Mds1
    steps:
      - action: host.ssh_command
        id: step1
        inputs:
          host: mds1
          run: touch test
        outputs:
          id: this.id
  configure_lnet:
    name: configure lnet
    needs:
      - add_mds1
    steps:
      - action: lnet.configure
        inputs:
          network: tcp0
          ethernet: eth1
          host: "${{needs.add_mds1.step1.outputs.id}}"
        id: step1
timeout: 5 minutes"#
            .trim();

        let doc = deserialize_input_document(s)?;

        // DB storage format
        let s = serde_json::to_string(&doc)?;

        let doc = deserialize_input_document(&s)?;

        insta::with_settings!({sort_maps => true}, {
            insta::assert_yaml_snapshot!(doc);
        });

        Ok(())
    }

    #[test]
    fn with_unknown_input() -> Result<(), InputDocumentErrors> {
        let s = r#"
version: 1
jobs:
    add_mds1:
        name: Add Mds1
        steps:
            - action: host.ssh_command
              id: step1
              inputs:
                  host: mds1
                  run: touch test
                  foo: bar
              outputs:
                  id: this.id
timeout: 2 minutes"#
            .trim();

        let errs = deserialize_input_document(s).err().unwrap();

        insta::assert_display_snapshot!(errs);

        Ok(())
    }

    #[test]
    fn with_action_after_inputs() -> Result<(), InputDocumentErrors> {
        let s = r#"
version: 1
jobs:
    add_mds1:
        name: Add Mds1
        steps:
            - id: step1
              inputs:
                host: mds1
                run: touch test
              action: host.ssh_command
              outputs:
                id: this.id
timeout: 2 minutes"#
            .trim();

        let err = deserialize_input_document(s).err().unwrap();

        insta::assert_display_snapshot!(err);

        Ok(())
    }

    #[test]
    fn with_no_defined_action() -> Result<(), InputDocumentErrors> {
        let s = r#"
version: 1
jobs:
    add_mds1:
        name: Add Mds1
        steps:
            - id: step1
              inputs:
                host: mds1
                run: touch test
              outputs:
                id: this.id
timeout: 2 minutes"#
            .trim();

        let err = deserialize_input_document(s).err().unwrap();

        insta::assert_display_snapshot!(err);

        Ok(())
    }

    #[test]
    fn with_missing_id() -> Result<(), InputDocumentErrors> {
        let s = r#"
version: 1
jobs:
  deploy_hosts:
    name: Deploy Hosts

    steps:
      - action: host.setup_planes_ssh
        inputs:
          host: node2
          cp_addr: node1
"#
        .trim();

        let err = deserialize_input_document(s).err().unwrap();

        insta::assert_display_snapshot!(err);

        Ok(())
    }

    #[test]
    fn without_inputs() -> Result<(), InputDocumentErrors> {
        let s = r#"
version: 1
jobs:
    add_mds1:
        name: Add Mds1
        steps:
            - id: step1
              action: host.ssh_command
              outputs:
timeout: 2 minutes"#
            .trim();

        let err = deserialize_input_document(s).err().unwrap();

        insta::assert_display_snapshot!(err);

        Ok(())
    }

    #[test]
    fn inputs_with_missing_required_fields() -> Result<(), InputDocumentErrors> {
        let s = r#"
version: 1
jobs:
    add_mds1:
        name: Add Mds1
        steps:
            - id: step1
              action: host.ssh_command
              inputs: {}
              outputs:
timeout: 2 minutes"#
            .trim();

        let err = deserialize_input_document(s).err().unwrap();

        insta::assert_display_snapshot!(err);

        Ok(())
    }

    #[test]
    fn input_invalid_input_array_length() -> Result<(), InputDocumentErrors> {
        let s = r#"
version: 1
jobs:
    create_filesystem_fs:
        name: Create Filesystem fs
        steps:
            - id: step1
              action: filesystem.create
              inputs:
                ost_volumes: []
                name: fs
                mgt_type: volume
                mgt: mgt
                mdt_volumes:
                  - mdt1
              outputs:
timeout: 2 minutes"#
            .trim();

        let err = deserialize_input_document(s).err().unwrap();

        match err.0[0] {
            InputDocumentError::ValidationErrors(_) => {}
            _ => panic!("Expected a validation error!"),
        }

        Ok(())
    }

    #[test]
    fn input_invalid_input_string_length() -> Result<(), InputDocumentErrors> {
        let s = r#"
version: 1
jobs:
    create_filesystem_fs:
        name: Create Filesystem fs
        steps:
            - id: step1
              action: filesystem.create
              inputs:
                ost_volumes:
                  - ost1
                name: ""
                mgt_type: volume
                mgt: mgt
                mdt_volumes:
                  - mdt1
              outputs:
timeout: 2 minutes"#
            .trim();

        let err = deserialize_input_document(s).err().unwrap();

        match err.0[0] {
            InputDocumentError::ValidationErrors(_) => {}
            _ => panic!("Expected a validation error!"),
        }

        Ok(())
    }

    #[test]
    fn input_invalid_field_type() -> Result<(), InputDocumentErrors> {
        let s = r#"
version: 1
jobs:
    create_filesystem_fs:
        name: Create Filesystem fs
        steps:
            - id: step1
              action: filesystem.create
              inputs:
                ost_volumes:
                  - ost1
                name:
                mgt_type: volume
                mgt: mgt
                mdt_volumes:
                  - mdt1
              outputs:
timeout: 2 minutes"#
            .trim();

        let err = deserialize_input_document(s).err().unwrap();

        match err.0[0] {
            InputDocumentError::SerdeYamlPathToError(_) => {}
            _ => {
                panic!("Expected a SerdeYamlPathToError error!")
            }
        }

        Ok(())
    }

    #[test]
    fn input_deploy_host() -> Result<(), InputDocumentErrors> {
        let s = std::include_str!("../../fixtures/deploy-hosts.yml");

        let doc = deserialize_input_document(s)?;

        insta::with_settings!({sort_maps => true}, {
            insta::assert_yaml_snapshot!(doc);
        });

        Ok(())
    }
}
