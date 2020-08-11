// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::sfa::HealthState;
#[cfg(feature = "postgres-interop")]
use crate::{schema::chroma_core_sfastoragesystem as ss, Executable};

#[derive(Debug, Clone)]
#[cfg_attr(feature = "postgres-interop", derive(Insertable, AsChangeset))]
#[cfg_attr(feature = "postgres-interop", table_name = "ss")]
pub struct SfaStorageSystem {
    pub uuid: String,
    pub platform: String,
    pub health_state_reason: String,
    pub health_state: HealthState,
    pub child_health_state: HealthState,
}

#[cfg(feature = "postgres-interop")]
impl SfaStorageSystem {
    pub fn all() -> ss::table {
        ss::table
    }
    pub fn upsert(x: Self) -> impl Executable {
        diesel::insert_into(Self::all())
            .values(x.clone())
            .on_conflict(ss::uuid)
            .do_update()
            .set(x)
    }
}
