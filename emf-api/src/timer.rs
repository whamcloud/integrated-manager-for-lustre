use crate::error::EmfApiError;
use emf_manager_client::{delete, get_client, put};
use emf_manager_env::{get_timer_addr, running_in_docker};
use std::time::Duration;

#[derive(serde::Serialize, Debug)]
pub struct TimerConfig {
    config_id: String,
    file_prefix: String,
    timer_config: String,
    service_config: String,
}

pub async fn configure_snapshot_timer(
    config_id: i32,
    fsname: String,
    interval: Duration,
    use_barrier: bool,
) -> Result<(), EmfApiError> {
    let emf_cmd = format!(
        r#"/bin/bash -c "/usr/bin/date +\"%%Y-%%m-%%dT%%TZ\" | xargs -I %% /usr/bin/emf snapshot create {} -c 'automatically created by EMF' {} {}-{}-%%""#,
        if use_barrier { "-b" } else { "" },
        fsname,
        config_id,
        fsname
    );

    let timer_config = format!(
        r#"# Automatically created by EMF

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
        r#"# Automatically created by EMF

[Unit]
Description=Create snapshot on filesystem {}
{}

[Service]
Type=oneshot
EnvironmentFile=/var/lib/chroma/emf-settings.conf
ExecStart={}
"#,
        fsname,
        if !running_in_docker() {
            "After=emf-manager.target"
        } else {
            ""
        },
        emf_cmd,
    );

    let config = TimerConfig {
        config_id: config_id.to_string(),
        file_prefix: "emf-snapshot".to_string(),
        timer_config,
        service_config,
    };

    let client = get_client()?;

    let url = format!("http://{}/configure/", get_timer_addr());
    tracing::debug!(
        "Sending snapshot interval config to timer service: {:?} {:?}",
        url,
        config
    );
    put(client, url.as_str(), config).await?;

    Ok(())
}

pub async fn remove_snapshot_timer(config_id: i32) -> Result<(), EmfApiError> {
    let client = get_client()?;

    delete(
        client,
        format!(
            "http://{}/unconfigure/emf-snapshot/{}",
            get_timer_addr(),
            config_id
        )
        .as_str(),
        serde_json::json!("{}"),
    )
    .await?;

    Ok(())
}
