// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::{CibError, ImlAgentError},
    cmd::cmd_output,
};
use elementtree::Element;
use iml_wire_types::{ComponentState, ConfigState, RunState, ServiceState};
use std::default::Default;

/// This processes <instance_attributes> section of a stonith
/// "<primitive>" type from the pacemaker cib.
///
/// There are two variables of concern in the attributes:
/// * pcmk_host_check -
///   - static-list - pcmk_host_list defines comma deliniated list of hosts
///     controlled by this fencing agent
///   - dynamic-list (default) - host list is derived from querying fencing
///     agent (assume same as "none")
///   - none - any host can fence any host
/// * pcmk_host_list - list of hosts controlled
///
fn check_instance_attr(elem: Option<&Element>, node: &str) -> Result<(), String> {
    if let Some(instance) = elem {
        let mut hl = "";
        let mut hl_set = false;
        let mut static_hc = false;
        for e in instance.children() {
            match e.get_attr("name") {
                Some("pcmk_host_list") => {
                    hl_set = true;
                    hl = e.get_attr("value").map_or("", |v| v);
                }
                Some("pcmk_host_check") => match e.get_attr("value") {
                    Some("static-list") => static_hc = true,
                    _ => return Ok(()),
                },
                _ => (),
            }
        }
        // pcmk_host_check
        // "none" -> any host can fence any host
        // "dynamic-list" -> ASSUME fence agent check
        // "static-list" -> only hosts specified in pcmk_host_list will work
        // MISSING -> if host list is missing, default to dynamic-list, else
        // check host list
        if static_hc || hl_set {
            let v: Vec<&str> = hl.split(',').collect();
            if !v.contains(&node) {
                return Err(format!("{} missing from host list", node));
            }
        }
    }
    Ok(())
}

/// This processes <meta_attributes> section of a stonith <primitive>
/// from the pacemaker cib
///
fn check_meta_attr(elem: Option<&Element>) -> Result<(), String> {
    if let Some(meta) = elem {
        for e in meta.children() {
            if Some("target-role") == e.get_attr("name") {
                match e.get_attr("value") {
                    Some("Started") => return Ok(()),
                    Some(other) => return Err(format!("role: {}", other)),
                    None => (),
                }
            }
        }
    }
    Ok(())
}

fn stonith_ok(
    elem: &Element,
    nodename: &str,
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
            if let Err(err) = check_meta_attr(elem.find("meta_attributes")) {
                Ok((false, format!("{} - {}", t, err), ConfigState::Other))
            } else if let Err(err) = check_instance_attr(elem.find("instance_attributes"), nodename)
            {
                Ok((false, format!("{} - {}", t, err), ConfigState::Other))
            } else {
                Ok((true, t.to_string(), ConfigState::Other))
            }
        }
    }
}

fn do_check_stonith(xml: &[u8], nodename: &str) -> Result<ComponentState<bool>, ImlAgentError> {
    let mut state = ComponentState {
        state: false,
        service: ServiceState::Configured(RunState::Setup),
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

pub async fn check_stonith(_: ()) -> Result<ComponentState<bool>, ImlAgentError> {
    let stonith = cmd_output(
        "cibadmin",
        vec!["--query", "--xpath", "//primitive[@class='stonith']"],
    )
    .await?;

    if !stonith.status.success() {
        return Ok(ComponentState {
            state: false,
            info: "No pacemaker".to_string(),
            ..Default::default()
        });
    }
    let node = cmd_output("crm_node", vec!["-n"]).await?;
    do_check_stonith(stonith.stdout.as_slice(), &String::from_utf8(node.stdout)?)
}

#[cfg(test)]
mod tests {
    use super::do_check_stonith;
    use iml_wire_types::{ComponentState, ConfigState, RunState, ServiceState};
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
                service: ServiceState::Configured(RunState::Setup),
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
                service: ServiceState::Configured(RunState::Setup),
                ..Default::default()
            }
        );
    }

    fn multihost_testxml_static<'a>() -> &'a [u8] {
        r#"<xpath-query>
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
          <nvpair name="pcmk_host_check" value="static-list" id="stonith-host1-instance_attributes-pcmk_host_check"/>
          <nvpair name="ipaddr" value="10.0.1.11" id="stonith-host1-instance_attributes-ipaddr"/>
          <nvpair name="login" value="root" id="stonith-host1-instance_attributes-login"/>
          <nvpair name="passwd" value="****" id="stonith-host1-instance_attributes-passwd"/>
          <nvpair name="lanplus" value="true" id="stonith-host1-instance_attributes-lanplus"/>
          <nvpair name="auth" value="md5" id="stonith-host1-instance_attributes-auth"/>
          <nvpair name="power_wait" value="5" id="stonith-host1-instance_attributes-power_wait"/>
          <nvpair name="method" value="onoff" id="stonith-host1-instance_attributes-method"/>
          <nvpair name="delay" value="15" id="stonith-host1-instance_attributes-delay"/>
          <nvpair name="privlvl" value="OPERATOR" id="stonith-host1-instance_attributes-privlvl"/>
          <nvpair name="pcmk_host_list" value="host2,host1" id="stonith-host1-instance_attributes-pcmk_host_list"/>
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
"#.as_bytes()
    }

    #[test]
    fn test_stonith_multi_fence_ipmilan_host0() {
        assert_eq!(
            do_check_stonith(multihost_testxml_static(), &"host0".to_string()).unwrap(),
            ComponentState {
                state: true,
                info: "fence_ipmilan".to_string(),
                config: ConfigState::Other,
                service: ServiceState::Configured(RunState::Setup),
                ..Default::default()
            }
        );
    }

    #[test]
    fn test_stonith_multi_fence_ipmilan_host1() {
        assert_eq!(
            do_check_stonith(multihost_testxml_static(), &"host1".to_string()).unwrap(),
            ComponentState {
                state: true,
                info: "fence_ipmilan".to_string(),
                config: ConfigState::Other,
                service: ServiceState::Configured(RunState::Setup),
                ..Default::default()
            }
        );
    }

    #[test]
    fn test_stonith_multi_fence_ipmilan_badhost() {
        assert_eq!(
            do_check_stonith(multihost_testxml_static(), &"badhost".to_string()).unwrap(),
            ComponentState {
                state: false,
                info: "No working fencing agents".to_string(),
                config: ConfigState::Other,
                service: ServiceState::Configured(RunState::Setup),
                ..Default::default()
            }
        );
    }

    fn multihost_testxml_dynamic<'a>() -> &'a [u8] {
        r#"<xpath-query>
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
      <primitive id="stonith-dynamic" class="stonith" type="fence_ipmilan">
        <instance_attributes id="stonith-dynamic-instance_attributes">
          <nvpair name="pcmk_host_check" value="dynamic-list" id="stonith-dynamic-instance_attributes-pcmk_host_check"/>
          <nvpair name="ipaddr" value="10.0.1.12" id="stonith-dynamic-instance_attributes-ipaddr"/>
          <nvpair name="login" value="root" id="stonith-dynamic-instance_attributes-login"/>
          <nvpair name="passwd" value="****" id="stonith-dynamic-instance_attributes-passwd"/>
          <nvpair name="lanplus" value="true" id="stonith-dynamic-instance_attributes-lanplus"/>
          <nvpair name="auth" value="md5" id="stonith-dynamic-instance_attributes-auth"/>
          <nvpair name="power_wait" value="5" id="stonith-dynamic-instance_attributes-power_wait"/>
          <nvpair name="method" value="onoff" id="stonith-dynamic-instance_attributes-method"/>
          <nvpair name="delay" value="15" id="stonith-dynamic-instance_attributes-delay"/>
          <nvpair name="privlvl" value="OPERATOR" id="stonith-dynamic-instance_attributes-privlvl"/>
        </instance_attributes>
        <meta_attributes id="stonith-dynamic-meta_attributes">
          <nvpair name="priority" value="9000" id="stonith-dynamic-meta_attributes-priority"/>
          <nvpair name="failure-timeout" value="20" id="stonith-dynamic-meta_attributes-failure-timeout"/>
          <nvpair id="stonith-dynamic-meta_attributes-target-role" name="target-role" value="Started"/>
        </meta_attributes>
        <operations>
          <op name="monitor" interval="20" timeout="240" id="stonith-dynamic-monitor-20"/>
        </operations>
      </primitive>
</xpath-query>
"#.as_bytes()
    }

    #[test]
    fn test_stonith_multi_fence_ipmilan_host_dynamic() {
        assert_eq!(
            do_check_stonith(multihost_testxml_dynamic(), &"host2".to_string()).unwrap(),
            ComponentState {
                state: true,
                info: "fence_ipmilan".to_string(),
                config: ConfigState::Other,
                service: ServiceState::Configured(RunState::Setup),
                ..Default::default()
            }
        );
    }
}
