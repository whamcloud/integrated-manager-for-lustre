// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{
    agent_error::{CibError, ImlAgentError},
    cmd::cmd_output,
};
use elementtree::Element;
use futures::Future;
use tracing::{span, Level};
use tracing_futures::Instrument;

fn stonith_ok(elem: &Element) -> Result<(bool, String), ImlAgentError> {
    match elem.get_attr("type") {
        None => Err(ImlAgentError::CibError(CibError(format!(
            "{} is missing type attribute",
            elem.tag()
        )))),
        Some("fence_chroma") => match elem.find("instance_attributes") {
            None => Ok((false, "fence_chroma - unconfigured".to_string())),
            Some(_) => Ok((true, "fence_chroma".to_string())),
        },
        Some(t) => Ok((true, t.to_string())),
        // @@TODO: This should check for node name in
        // instance_attributes:pcmk_host_list if
        // pcmk_host_check=static-list

        // @@TODO: This should check meta_attributes:target-role is
        // not Stopped (disabled agent)
    }
}

fn _check_stonith(output: &[u8]) -> Result<(bool, String), ImlAgentError> {
    match Element::from_reader(output) {
        Err(err) => Err(ImlAgentError::XmlError(err)),
        Ok(elem) => match elem.tag().name() {
            "primitive" => stonith_ok(&elem),
            "xpath-query" => {
                for el in elem.find_all("primitive") {
                    if let Ok((true, msg)) = stonith_ok(el) {
                        return Ok((true, msg));
                    }
                }
                Ok((false, "No working fencing agents".to_string()))
            }
            tag => Err(ImlAgentError::CibError(CibError(format!(
                "Unknown first tag {}",
                tag
            )))),
        },
    }
}

pub fn check_stonith(_: ()) -> impl Future<Item = (bool, String), Error = ImlAgentError> {
    cmd_output(
        "cibadmin",
        &["--query", "--xpath", "//primitive[@class='stonith']"],
    )
    .instrument(span!(Level::INFO, "Read cib"))
    .and_then(|x| {
        if !x.status.success() {
            return Ok((false, "No pacemaker".to_string()));
        }
        _check_stonith(x.stdout.as_slice())
    })
    .from_err()
}

#[cfg(test)]
mod tests {
    use super::_check_stonith;
    use crate::agent_error;

    #[test]
    fn test_stonith_unconfigured_fence_chroma() -> agent_error::Result<()> {
        let testxml = r#"<primitive class="stonith" id="st-fencing" type="fence_chroma"/>"#;
        assert_eq!(
            _check_stonith(&testxml.as_bytes()).unwrap(),
            (false, "fence_chroma - unconfigured".to_string())
        );

        Ok(())
    }

    #[test]
    fn test_stonith_bad_xml() -> agent_error::Result<()> {
        let testxml = r#"<badtag class="stonith" id="st-fencing" type="fence_chroma"/>"#;
        assert_eq!(
            format!("{}", _check_stonith(&testxml.as_bytes()).unwrap_err()),
            "Unknown first tag badtag".to_string()
        );

        Ok(())
    }

    #[test]
    fn test_stonith_fence_vbox() -> agent_error::Result<()> {
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
            _check_stonith(&testxml.as_bytes()).unwrap(),
            (true, "fence_vbox".to_string())
        );
        Ok(())
    }

    #[test]
    fn test_stonith_multi_fence_ipmilan() -> agent_error::Result<()> {
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
          <nvpair name="pcmk_host_list" value="host1" id="stonith-host1-instance_attributes-pcmk_host_list"/>
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
            _check_stonith(&testxml.as_bytes()).unwrap(),
            (true, "fence_ipmilan".to_string())
        );
        Ok(())
    }
}
