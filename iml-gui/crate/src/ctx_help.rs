use crate::route::Route;

pub(crate) trait CtxHelp {
    fn help_link(&self) -> Option<String>;
}

impl<'a> CtxHelp for Route<'a> {
    fn help_link(&self) -> Option<String> {
        let anchor = match self {
            Route::Dashboard => Some("9.1"),
            Route::Server => Some("9.3.1"),
            Route::PowerControl => Some("9.3.2"),
            Route::Filesystem => Some("9.3.3"),
            // Route::Hsm => Some("9.3.4"),
            // Route::Storage => Some("9.3.5"),
            Route::User => Some("9.3.6"),
            Route::Volume => Some("9.3.7"),
            Route::Mgt => Some("9.3.8"),
            Route::Jobstats => Some("9.4"),
            Route::Logs => Some("9.5"),
            Route::Activity => Some("9.6"),
            Route::FilesystemDetail(_) => Some("9.1.1"),
            Route::ServerDetail(_) => Some("9.3.1.1"),
            _ => None,
        };
        anchor.map(|anc| format!("#{}", anc))
    }
}
