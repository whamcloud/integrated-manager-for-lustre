// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, cmd::cmd_output};
use elementtree::Element;
use futures::Future;
use tracing::{span, Level};
use tracing_futures::Instrument;

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
            Ok(elem) => match elem.get_attr("type") {
                Some("fence_chroma") => match elem.find("instance_attributes") {
                    None => Ok((false, "fence_chroma - unconfigured".to_string())),
                    Some(_) => Ok((true, "fence_chroma".to_string())),
                },
                // @@ Should this check pcmk_host_list?
                Some("fence_ipmilan") => Ok((true, "fence_ipmilan".to_string())),
                Some(t) => Ok((false, format!("{} - unknown type", t))),
                None => Err(ImlAgentError::UnexpectedStatusError),
            },
        }
    })
    .from_err()
}
