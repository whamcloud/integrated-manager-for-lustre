use emf_command_utils::CmdUtilError;
use emf_manager_client::EmfManagerClientError;
use tokio::time::Instant;

pub mod client_monitor;
pub mod retention;

#[derive(thiserror::Error, Debug)]
pub enum Error {
    #[error(transparent)]
    EmfCmdUtilError(#[from] CmdUtilError),
    #[error(transparent)]
    EmfManagerClientError(#[from] EmfManagerClientError),
    #[error(transparent)]
    EmfGraphqlQueriesError(#[from] emf_graphql_queries::Errors),
    #[error(transparent)]
    EmfPostgresError(#[from] emf_postgres::sqlx::Error),
    #[error(transparent)]
    EmfInfluxError(#[from] emf_influx::Error),
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
