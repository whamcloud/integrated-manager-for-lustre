use iml_command_utils::CmdUtilError;
use iml_manager_client::ImlManagerClientError;
use tokio::time::Instant;

pub mod client_monitor;
pub mod policy;
pub mod retention;

#[derive(thiserror::Error, Debug)]
pub enum Error {
    #[error(transparent)]
    ImlCmdUtilError(#[from] CmdUtilError),
    #[error(transparent)]
    ImlManagerClientError(#[from] ImlManagerClientError),
    #[error(transparent)]
    ImlGraphqlQueriesError(#[from] iml_graphql_queries::Errors),
    #[error(transparent)]
    ImlPostgresError(#[from] iml_postgres::sqlx::Error),
    #[error(transparent)]
    ImlInfluxError(#[from] iml_influx::Error),
}

#[derive(Debug, PartialEq, Eq, Hash, Clone)]
pub enum MonitorState {
    Monitoring(u64),
    CountingDown(Instant),
}

#[derive(Debug, serde::Serialize, serde::Deserialize)]
pub struct FsStats {
    bytes_total: u64,
    bytes_free: u64,
    bytes_avail: u64,
}
