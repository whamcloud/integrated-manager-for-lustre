// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{generated::css_classes::C, Msg};
use chrono::{offset::Local, Datelike};
use emf_wire_types::{Branding, Conf};
use seed::{prelude::*, *};

pub fn view(conf: &Conf) -> impl View<Msg> {
    let year = Local::now().year();

    let footer_string = match conf.branding {
        Branding::Whamcloud => format!(
            "EXAScaler Management Framework software {} is Copyright © ",
            conf.version
        ),
        _ => {
            if let Some(version) = &conf.exa_version {
                format!("© 2020 - DDN EXAScaler v{} ", version)
            } else {
                "© 2020 - DDN EXAScaler ".to_string()
            }
        }
    };

    let footer_text = match conf.branding {
        Branding::Whamcloud => div![
            footer_string,
            year.to_string(),
            " DDN. All rights reserved.".to_string(),
        ],
        _ => div![footer_string],
    };

    footer![
        class![C.h_5, C.flex, C.justify_center],
        div![class![C.px_5, C.text_sm, C.items_center,], footer_text]
    ]
}
