#[derive(Default)]
pub struct ServerDate {
    date: Option<chrono::DateTime<chrono::offset::FixedOffset>>,
}

impl ServerDate {
    pub(crate) fn set(self: &mut Self, date: chrono::DateTime<chrono::offset::FixedOffset>) {
        self.date = Some(date);
    }
    pub(crate) fn timeago(&self, date: chrono::DateTime<chrono::offset::FixedOffset>) -> String {
        self.date
            .map(|sd| format!("{}", chrono_humanize::HumanTime::from(date - sd)))
            .unwrap_or_else(|| date.to_rfc2822())
    }
}
