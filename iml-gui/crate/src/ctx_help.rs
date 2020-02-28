use crate::route::Route;

pub(crate) trait CtxHelp {
    fn help_link(&self) -> Option<String>;
}

impl<'a> CtxHelp for Route<'a> {
    fn help_link(&self) -> Option<String> {
        let anchor = match self {
            Route::Dashboard => Some("9.1"),
            Route::Servers => Some("9.3.1"),
            Route::PowerControl => Some("9.3.2"),
            Route::Filesystems => Some("9.3.3"),
            // Route::Hsm => Some("9.3.4"),
            // Route::Storage => Some("9.3.5"),
            Route::Users => Some("9.3.6"),
            Route::Volumes => Some("9.3.7"),
            Route::Mgt => Some("9.3.8"),
            Route::Jobstats => Some("9.4"),
            Route::Logs => Some("9.5"),
            Route::Filesystem(_) => Some("9.1.1"),
            Route::Server(_) => Some("9.3.1.1"),
            _ => None,
        };
        anchor.map(|anc| format!("#{}", anc))
    }
}
