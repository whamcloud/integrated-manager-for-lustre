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
        match Element::from_reader(x.stdout.as_slice()) {
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
    })
    .from_err()
}
