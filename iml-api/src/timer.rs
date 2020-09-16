use crate::error::ImlApiError;
use iml_manager_client::{get_client, put};
use std::time::Duration;

#[derive(serde::Serialize)]
pub struct TimerConfig {
    config_id: i32,
    timer_config: String,
    service_config: String,
}

pub async fn configure_snapshot_timer(
    config_id: i32,
    fsname: String,
    interval: Duration,
) -> Result<(), ImlApiError> {
    let iml_cmd = format!(
        r#"date +"%Y-%m-%dT%T%z" | xargs -I % echo "iml snapshot create {} {}-{}-%"#,
        fsname, config_id, fsname
    );

    let timer_config = format!(
        r#"# Automatically created by IML

[Unit]
Description=Create snapshot on filesystem {}

[Timer]
OnActiveSec={}
OnUnitActiveSec={}
AccuracySec=1us
Persistent=true

[Install]
WantedBy=timers.target
"#,
        fsname,
        interval.as_secs(),
        interval.as_secs()
    );

    let service_config = format!(
        r#"# Automatically created by IML

[Unit]
Description=Create snapshot on filesystem {}

[Service]
Type=oneshot
EnvironmentFile=/var/lib/chroma/iml-settings.conf
ExecStart={}
"#,
        fsname, iml_cmd
    );

    let config = TimerConfig {
        config_id,
        timer_config,
        service_config,
    };

    let client = get_client()?;

    put(client, "/timer/configure/", config).await?;

    Ok(())
}
