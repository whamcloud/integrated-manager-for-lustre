// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::sfa::{SfaDiskDrive, SfaDiskSlot, SfaEnclosure, SfaJob, SfaPowerSupply};
use std::convert::TryInto;
use tokio_postgres::Row;

impl From<Row> for SfaEnclosure {
    fn from(row: Row) -> Self {
        Self {
            index: row.get::<_, i32>("index"),
            element_name: row.get("element_name"),
            health_state: row
                .get::<_, i16>("health_state")
                .try_into()
                .unwrap_or_default(),
            health_state_reason: row.get("health_state_reason"),
            model: row.get("model"),
            position: row.get::<_, i16>("position"),
            enclosure_type: row
                .get::<_, i16>("enclosure_type")
                .try_into()
                .unwrap_or_default(),
            storage_system: row.get("storage_system"),
            canister_location: row.get("canister_location"),
        }
    }
}

impl From<Row> for SfaDiskDrive {
    fn from(row: Row) -> Self {
        Self {
            index: row.get::<_, i32>("index"),
            child_health_state: row
                .get::<_, i16>("child_health_state")
                .try_into()
                .unwrap_or_default(),
            failed: row.get("failed"),
            health_state_reason: row.get("health_state_reason"),
            health_state: row
                .get::<_, i16>("health_state")
                .try_into()
                .unwrap_or_default(),
            member_index: row.get::<_, Option<i16>>("member_index"),
            member_state: row
                .get::<_, i16>("member_state")
                .try_into()
                .unwrap_or_default(),
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
            sub_target_type: row
                .get::<_, Option<i16>>("sub_target_type")
                .map(|x| x.try_into().unwrap_or_default()),
            job_type: row.get::<_, i16>("job_type").try_into().unwrap_or_default(),
            state: row.get::<_, i16>("state").try_into().unwrap_or_default(),
            storage_system: row.get("storage_system"),
        }
    }
}

impl From<Row> for SfaDiskSlot {
    fn from(row: Row) -> Self {
        Self {
            index: row.get::<_, i32>("index"),
            enclosure_index: row.get::<_, i32>("enclosure_index"),
            disk_drive_index: row.get::<_, i32>("disk_drive_index"),
            storage_system: row.get("storage_system"),
        }
    }
}

impl From<Row> for SfaPowerSupply {
    fn from(row: Row) -> Self {
        Self {
            index: row.get::<_, i32>("index"),
            health_state: row
                .get::<_, i16>("health_state")
                .try_into()
                .unwrap_or_default(),
            health_state_reason: row.get("health_state_reason"),
            enclosure_index: row.get::<_, i32>("enclosure_index"),
            position: row.get::<_, i16>("position"),
            storage_system: row.get("storage_system"),
        }
    }
}
