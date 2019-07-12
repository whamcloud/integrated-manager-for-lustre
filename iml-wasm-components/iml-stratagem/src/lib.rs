use iml_grafana_chart::grafana_chart;
use seed::prelude::*;

static DASHBOARD_ID: &str = "OBdCS5IWz";
static DASHBOARD_NAME: &str = "stratagem";

pub fn size_distribution_chart_view<T>() -> El<T> {
    grafana_chart(DASHBOARD_ID, DASHBOARD_NAME, "10s", 2, "100%", "600")
}
