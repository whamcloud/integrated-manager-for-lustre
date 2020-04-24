// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::sfa::{SfaDiskDrive, SfaEnclosure, SfaJob};
use tokio_postgres::Row;

impl From<Row> for SfaEnclosure {
    fn from(row: Row) -> Self {
        Self {
            index: row.get::<_, i32>("index"),
            element_name: row.get("element_name"),
            health_state: row.get::<_, i16>("health_state").into(),
            health_state_reason: row.get("health_state_reason"),
            position: row.get::<_, i16>("position"),
            enclosure_type: row.get::<_, i16>("enclosure_type").into(),
            storage_system: row.get("storage_system"),
            canister_location: row.get("canister_location"),
        }
    }
}

impl From<Row> for SfaDiskDrive {
    fn from(row: Row) -> Self {
        Self {
            index: row.get::<_, i32>("index"),
            child_health_state: row.get::<_, i16>("child_health_state").into(),
            failed: row.get("failed"),
            health_state_reason: row.get("health_state_reason"),
            health_state: row.get::<_, i16>("health_state").into(),
            member_index: row.get::<_, Option<i16>>("member_index"),
            member_state: row.get::<_, i16>("member_state").into(),
            enclosure_index: row.get::<_, i32>("enclosure_index"),
            slot_number: row.get::<_, i32>("slot_number"),
            storage_system: row.get("storage_system"),
        }
    }
}

impl From<Row> for SfaJob {
    fn from(row: Row) -> Self {
        Self {
            index: row.get::<_, i32>("index"),
            sub_target_index: row.get::<_, Option<i32>>("sub_target_index"),
            sub_target_type: row.get::<_, Option<i16>>("sub_target_type"),
            job_type: row.get::<_, i16>("job_type").into(),
            state: row.get::<_, i16>("state").into(),
            storage_system: row.get("storage_system"),
        }
    }
}
