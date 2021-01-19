// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::route::Route;

pub(crate) trait CtxHelp {
    fn help_link(&self) -> Option<String>;
}

impl<'a> CtxHelp for Route<'a> {
    fn help_link(&self) -> Option<String> {
        let anchor = match self {
            Route::Dashboard => Some("9.1"),
            Route::Servers => Some("9.3.1"),
            Route::Filesystems => Some("9.3.3"),
            Route::Users => Some("9.3.6"),
            Route::Volumes => Some("9.3.7"),
            Route::Mgt => Some("9.3.8"),
            Route::Jobstats => Some("9.4"),
            Route::Filesystem(_) => Some("9.1.1"),
            Route::Server(_) => Some("9.3.1.1"),
            _ => None,
        };
        anchor.map(|anc| format!("#{}", anc))
    }
}
