use iml_wire_types::{Alert, AlertSeverity};

/// Ask user's permission to display notifications.
/// Should be called on application's load.
pub(crate) fn request_permission() {
    if web_sys::Notification::permission()
        == web_sys::NotificationPermission::Default
    {
        web_sys::Notification::request_permission().unwrap();
    }
}

/// Create and show to user (if permitted) a notification,
/// if the alert is active and severe enough.
pub(crate) fn display_alert(a: &Alert) {
    if a.active.unwrap_or(false) && a.severity > AlertSeverity::INFO {
        let n = web_sys::Notification::new_with_options(
            a.message.as_str(),
            web_sys::NotificationOptions::new()
                .tag(&"iml")
                .icon(&"/favicon.ico"),
        )
        .unwrap();

        seed::set_timeout(Box::new(move || n.close()), 5000);
    }
}
