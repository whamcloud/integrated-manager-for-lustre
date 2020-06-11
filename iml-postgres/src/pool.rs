// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub use deadpool_postgres::{Client, Pool, PoolError, config::ConfigError};

use iml_manager_env::get_db_conn_hash;
use tokio_postgres::NoTls;
    
pub async fn pool() -> Result<Pool, ConfigError> {
    let mut config = deadpool_postgres::Config::default();
    let mut db_conn = get_db_conn_hash();

    config.host = db_conn.remove("host");
    config.user = db_conn.remove("user");
    config.password = db_conn.remove("password");
    config.dbname = db_conn.remove("dbname");
    config.application_name = db_conn.remove("application_name");

    config.create_pool(NoTls)
}
