// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{generated::css_classes::C, Msg};
use chrono::{offset::Local, Datelike};
use iml_wire_types::{Branding, Conf};
use seed::{prelude::*, *};

pub fn view(conf: &Conf) -> impl View<Msg> {
    let year = Local::now().year();

    let footer_string = match conf.branding {
        Branding::Whamcloud => format!(
            "Integrated Manager for Lustre software {} is Copyright © ",
            conf.version
        ),
        _ => {
            if let Some(version) = &conf.exa_version {
                format!("Exascaler software {} is Copyright © ", version)
            } else {
                "Exascaler software is Copyright © ".to_string()
            }
        }
    };

    footer![
        class![C.h_5, C.flex, C.justify_center],
        div![
            class![C.px_5, C.text_sm, C.items_center,],
            footer_string,
            &year.to_string(),
            " DDN. All rights reserved.",
        ]
    ]
}
