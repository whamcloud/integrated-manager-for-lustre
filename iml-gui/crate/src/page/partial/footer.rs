// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{generated::css_classes::C, Msg};
use chrono::{offset::Local, Datelike};
use iml_wire_types::Conf;
use seed::{prelude::*, *};

pub fn view(conf: Conf) -> impl View<Msg> {
    let year = Local::now().year();
    let mut footer_string =  format!("Integrated Manager for Lustre software {} is Copyright © ", conf.version);
    
    if conf.branding != Branding::Whamcloud {
        footer_string = format!("EXAScaler software {} is Copyright © ", conf.exascaler_version);
    }
    footer![
        class![C.h_5, C.flex, C.justify_center],
        div![
            class![C.px_5, C.text_sm, C.items_center,],
            "Integrated Manager for Lustre software 6.0.0-1 is Copyright © ",
            &year.to_string(),
            " DDN. All rights reserved.",
        ]
    ]
}
