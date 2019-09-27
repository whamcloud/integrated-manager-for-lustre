// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::{CibError, ImlAgentError},
    cmd::cmd_output,
};
use elementtree::Element;
use futures::Future;
use iml_wire_types::{ComponentState, ConfigState, ServiceState};
use std::default::Default;
use std::process::Command;
use tracing::{span, Level};
use tracing_futures::Instrument;

fn inst_attr_problem(elem: &Option<&Element>, node: &String) -> Option<String> {
    match elem {
        None => None,
        Some(instance) => {
            let mut hc: Option<bool> = None;
            let mut hl: Option<bool> = None;
            for e in instance.children() {
                match e.get_attr("name") {
                    Some("pcmk_host_list") => match e.get_attr("value") {
                        None => return None,
                        Some(val) => {
                            if val.contains(node) {
                                match hc {
                                    Some(true) => return None,
                                    Some(false) => {
                                        return Some(format!(
                                            "{} missing from pcmk_host_list",
                                            node
                                        ))
                                    }
                                    None => hl = Some(true),
                                }
                            } else {
                                hl = Some(false);
                            }
                        }
                    },
                    Some("pcmk_host_check") => match e.get_attr("value") {
                        Some("static-list") => match hl {
                            Some(true) => return None,
                            Some(false) => {
                                return Some(format!("{} missing from pcmk_host_list", node))
                            }
                            None => hc = Some(true),
                        },
                        _ => return None,
                    },
                    _ => (),
                }
            }
            None
        }
    }
}

fn meta_attr_problem(elem: &Option<&Element>) -> Option<String> {
    match elem {
        None => None,
        Some(meta) => {
            for e in meta.children() {
                match e.get_attr("name") {
                    Some("target-role") => match e.get_attr("value") {
                        Some("Started") => return None,
                        Some(other) => return Some(format!("role: {}", other)),
                        None => (),
                    },
                    _ => (),
                }
            }
            None
        }
    }
}

fn stonith_ok(
    elem: &Element,
    nodename: &String,
) -> Result<(bool, String, ConfigState), ImlAgentError> {
    match elem.get_attr("type") {
        None => Err(ImlAgentError::CibError(CibError(format!(
            "{} is missing type attribute",
            elem.tag()
        )))),
        Some("fence_chroma") => match elem.find("instance_attributes") {
            None => Ok((
                false,
                "fence_chroma - unconfigured".to_string(),
                ConfigState::IML,
            )),
            Some(_) => Ok((true, "fence_chroma".to_string(), ConfigState::IML)),
        },
        Some(t) => {
            if let Some(err) = meta_attr_problem(&elem.find("meta_attributes")) {
                Ok((false, format!("{} - {}", t, err), ConfigState::Other))
            } else if let Some(err) = inst_attr_problem(&elem.find("instance_attributes"), nodename)
            {
                Ok((false, format!("{} - {}", t, err), ConfigState::Other))
            } else {
                Ok((true, t.to_string(), ConfigState::Other))
            }
        }
    }
}

fn do_check_stonith(xml: &[u8], nodename: &String) -> Result<ComponentState<bool>, ImlAgentError> {
    let mut state = ComponentState {
        state: false,
        service: ServiceState::Setup,
        ..Default::default()
    };

    match Element::from_reader(xml) {
        Err(err) => Err(ImlAgentError::XmlError(err)),
        Ok(elem) => match elem.tag().name() {
            "primitive" => {
                let (st, msg, cs) = stonith_ok(&elem, nodename)?;
                state.config = cs;
                state.info = msg;
                state.state = st;
                Ok(state)
            }
            "xpath-query" => {
                state.info = "No working fencing agents".to_string();
                state.config = ConfigState::Other;
                for el in elem.find_all("primitive") {
                    if let Ok((true, msg, cs)) = stonith_ok(el, nodename) {
                        state.config = cs;
                        state.state = true;
                        state.info = msg;
                        break;
                    }
                }
                Ok(state)
            }
            tag => Err(ImlAgentError::CibError(CibError(format!(
                "Unknown first tag {}",
                tag
            )))),
        },
    }
}

pub fn check_stonith(_: ()) -> impl Future<Item = ComponentState<bool>, Error = ImlAgentError> {
    cmd_output(
        "cibadmin",
        &["--query", "--xpath", "//primitive[@class='stonith']"],
    )
    .instrument(span!(Level::INFO, "Read cib"))
    .and_then(|x| {
        if !x.status.success() {
            return Ok(ComponentState {
                state: false,
                info: "No pacemaker".to_string(),
                ..Default::default()
            });
        }
        let cmd = Command::new("crm_node").args(&["-n"]).output()?;
        do_check_stonith(x.stdout.as_slice(), &String::from_utf8(cmd.stdout)?)
    })
    .from_err()
}

#[cfg(test)]
mod tests {
    use super::do_check_stonith;
    use crate::agent_error;
    use iml_wire_types::{ComponentState, ConfigState, ServiceState};
    use std::default::Default;

    #[test]
    fn test_stonith_unconfigured_fence_chroma() {
        let testxml = r#"<primitive class="stonith" id="st-fencing" type="fence_chroma"/>"#;

        assert_eq!(
            do_check_stonith(&testxml.as_bytes(), &"host0".to_string()).unwrap(),
            ComponentState {
                state: false,
                info: "fence_chroma - unconfigured".to_string(),
                config: ConfigState::IML,
                service: ServiceState::Setup,
                ..Default::default()
            }
        );
    }

    #[test]
    fn test_stonith_bad_xml() {
        let testxml = r#"<badtag class="stonith" id="st-fencing" type="fence_chroma"/>"#;
        assert_eq!(
            format!(
                "{}",
                do_check_stonith(&testxml.as_bytes(), &"host0".to_string()).unwrap_err()
            ),
            "Unknown first tag badtag".to_string()
        );
    }

    #[test]
    fn test_stonith_fence_vbox() {
        let testxml = r#"<primitive class="stonith" id="vboxfence" type="fence_vbox">
    <instance_attributes id="vboxfence-instance_attributes">
      <nvpair id="vboxfence-instance_attributes-identity_file" name="identity_file" value="/home/nclark/.ssh/id_rsa"/>
      <nvpair id="vboxfence-instance_attributes-ipaddr" name="ipaddr" value="stitch"/>
      <nvpair id="vboxfence-instance_attributes-login" name="login" value="nclark"/>
    </instance_attributes>
    <operations>
      <op id="vboxfence-monitor-interval-60s" interval="60s" name="monitor"/>
    </operations>
  </primitive>
"#;

        assert_eq!(
            do_check_stonith(&testxml.as_bytes(), &"host0".to_string()).unwrap(),
            ComponentState {
                state: true,
                info: "fence_vbox".to_string(),
                config: ConfigState::Other,
                service: ServiceState::Setup,
                ..Default::default()
            }
        );
    }

    #[test]
    fn test_stonith_multi_fence_ipmilan() {
        let testxml = r#"<xpath-query>
      <primitive id="stonith-host0" class="stonith" type="fence_ipmilan">
        <instance_attributes id="stonith-host0-instance_attributes">
          <nvpair name="pcmk_host_list" value="host0" id="stonith-host0-instance_attributes-pcmk_host_list"/>
          <nvpair name="ipaddr" value="10.0.1.10" id="stonith-host0-instance_attributes-ipaddr"/>
          <nvpair name="login" value="root" id="stonith-host0-instance_attributes-login"/>
          <nvpair name="passwd" value="****" id="stonith-host0-instance_attributes-passwd"/>
          <nvpair name="lanplus" value="true" id="stonith-host0-instance_attributes-lanplus"/>
          <nvpair name="auth" value="md5" id="stonith-host0-instance_attributes-auth"/>
          <nvpair name="power_wait" value="5" id="stonith-host0-instance_attributes-power_wait"/>
          <nvpair name="method" value="onoff" id="stonith-host0-instance_attributes-method"/>
          <nvpair name="delay" value="15" id="stonith-host0-instance_attributes-delay"/>
          <nvpair name="privlvl" value="OPERATOR" id="stonith-host0-instance_attributes-privlvl"/>
          <nvpair name="pcmk_host_check" value="static-list" id="stonith-host0-instance_attributes-pcmk_host_check"/>
        </instance_attributes>
        <meta_attributes id="stonith-host0-meta_attributes">
          <nvpair name="priority" value="9000" id="stonith-host0-meta_attributes-priority"/>
          <nvpair name="failure-timeout" value="20" id="stonith-host0-meta_attributes-failure-timeout"/>
          <nvpair id="stonith-host0-meta_attributes-target-role" name="target-role" value="Started"/>
        </meta_attributes>
        <operations>
          <op name="monitor" interval="20" timeout="240" id="stonith-host0-monitor-20"/>
        </operations>
      </primitive>
      <primitive id="stonith-host1" class="stonith" type="fence_ipmilan">
        <instance_attributes id="stonith-host1-instance_attributes">
          <nvpair name="pcmk_host_list" value="host2,host1" id="stonith-host1-instance_attributes-pcmk_host_list"/>
          <nvpair name="ipaddr" value="10.0.1.11" id="stonith-host1-instance_attributes-ipaddr"/>
          <nvpair name="login" value="root" id="stonith-host1-instance_attributes-login"/>
          <nvpair name="passwd" value="****" id="stonith-host1-instance_attributes-passwd"/>
          <nvpair name="lanplus" value="true" id="stonith-host1-instance_attributes-lanplus"/>
          <nvpair name="auth" value="md5" id="stonith-host1-instance_attributes-auth"/>
          <nvpair name="power_wait" value="5" id="stonith-host1-instance_attributes-power_wait"/>
          <nvpair name="method" value="onoff" id="stonith-host1-instance_attributes-method"/>
          <nvpair name="delay" value="15" id="stonith-host1-instance_attributes-delay"/>
          <nvpair name="privlvl" value="OPERATOR" id="stonith-host1-instance_attributes-privlvl"/>
          <nvpair name="pcmk_host_check" value="static-list" id="stonith-host1-instance_attributes-pcmk_host_check"/>
        </instance_attributes>
        <meta_attributes id="stonith-host1-meta_attributes">
          <nvpair name="priority" value="9000" id="stonith-host1-meta_attributes-priority"/>
          <nvpair name="failure-timeout" value="20" id="stonith-host1-meta_attributes-failure-timeout"/>
          <nvpair id="stonith-host1-meta_attributes-target-role" name="target-role" value="Started"/>
        </meta_attributes>
        <operations>
          <op name="monitor" interval="20" timeout="240" id="stonith-host1-monitor-20"/>
        </operations>
      </primitive>
</xpath-query>
"#;
        assert_eq!(
            do_check_stonith(&testxml.as_bytes(), &"host0".to_string()).unwrap(),
            ComponentState {
                state: true,
                info: "fence_ipmilan".to_string(),
                config: ConfigState::Other,
                service: ServiceState::Setup,
                ..Default::default()
            }
        );

        assert_eq!(
            do_check_stonith(&testxml.as_bytes(), &"host1".to_string()).unwrap(),
            ComponentState {
                state: true,
                info: "fence_ipmilan".to_string(),
                config: ConfigState::Other,
                service: ServiceState::Setup,
                ..Default::default()
            }
        );

        assert_eq!(
            do_check_stonith(&testxml.as_bytes(), &"badhost".to_string()).unwrap(),
            ComponentState {
                state: false,
                info: "No working fencing agents".to_string(),
                config: ConfigState::Other,
                service: ServiceState::Setup,
                ..Default::default()
            }
        );
    }
}
