// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

#[derive(Debug)]
pub enum ImlStatsError {
    InfluxDbError(influxdb::Error),
}

impl std::fmt::Display for ImlStatsError {
    fn fmt(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
        match *self {
            ImlStatsError::InfluxDbError(ref err) => write!(f, "{}", err),
        }
    }
}

impl std::error::Error for ImlStatsError {
    fn source(&self) -> Option<&(dyn std::error::Error + 'static)> {
        match *self {
            ImlStatsError::InfluxDbError(_) => None,
        }
    }
}
