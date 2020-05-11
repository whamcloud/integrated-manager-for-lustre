// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub use crate::models::ChromaCoreServerprofile;
use crate::{
    schema::{
        chroma_core_serverprofile as sp, chroma_core_serverprofile_repolist as rl,
        chroma_core_serverprofilepackage as pl,
    },
    Executable,
};
use diesel::{dsl, prelude::*};
use std::collections::HashSet;

pub type Table = sp::table;
pub type Name = dsl::Eq<sp::name, String>;

impl ChromaCoreServerprofile {
    pub fn all() -> Table {
        sp::table
    }
    pub fn with_name(name: impl ToString) -> Name {
        sp::name.eq(name.to_string())
    }
}

#[derive(serde::Deserialize)]
pub struct UserProfile {
    pub corosync: bool,
    pub corosync2: bool,
    pub initial_state: String,
    pub managed: bool,
    pub name: String,
    pub ntp: bool,
    pub pacemaker: bool,
    pub packages: HashSet<String>,
    pub repolist: HashSet<String>,
    pub ui_description: String,
    pub ui_name: String,
    pub worker: bool,
}

impl From<UserProfile> for ChromaCoreServerprofile {
    fn from(x: UserProfile) -> Self {
        Self {
            name: x.name,
            ui_name: x.ui_name,
            ui_description: x.ui_description,
            managed: x.managed,
            worker: x.worker,
            user_selectable: true,
            initial_state: x.initial_state,
            ntp: x.ntp,
            corosync: x.corosync,
            corosync2: x.corosync2,
            pacemaker: x.pacemaker,
            default: false,
        }
    }
}

pub fn remove_profile_by_name(
    name: impl ToString,
) -> (impl Executable, impl Executable, impl Executable) {
    let e1 = diesel::delete(rl::table).filter(rl::serverprofile_id.eq(name.to_string()));

    let e2 = diesel::delete(pl::table).filter(pl::server_profile_id.eq(name.to_string()));

    let e3 = diesel::delete(sp::table).filter(ChromaCoreServerprofile::with_name(name.to_string()));

    (e1, e2, e3)
}

pub fn upsert_user_profile(u: UserProfile) -> (impl Executable, impl Executable, impl Executable) {
    let name = u.name.clone();

    let repos: Vec<_> = u
        .repolist
        .iter()
        .cloned()
        .map(|x| (rl::serverprofile_id.eq(name.clone()), rl::repo_id.eq(x)))
        .collect();

    let packages: Vec<_> = u
        .packages
        .iter()
        .cloned()
        .map(|x| {
            (
                pl::package_name.eq(x),
                pl::server_profile_id.eq(name.clone()),
            )
        })
        .collect();

    let x = ChromaCoreServerprofile::from(u);

    let e1 = diesel::insert_into(sp::table)
        .values(x.clone())
        .on_conflict(sp::name)
        .do_update()
        .set(x);

    let e2 = diesel::insert_into(rl::table)
        .values(repos)
        .on_conflict_do_nothing();

    let e3 = diesel::insert_into(pl::table)
        .values(packages)
        .on_conflict_do_nothing();

    (e1, e2, e3)
}
