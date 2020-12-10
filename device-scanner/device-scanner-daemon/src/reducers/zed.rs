// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::error::{Error, Result};
use device_types::{
    state,
    zed::{prop, zfs, zpool, PoolCommand},
};
use std::result;

pub fn into_zed_events(xs: Vec<libzfs_types::Pool>) -> state::ZedEvents {
    xs.into_iter().map(|p| (p.guid, p)).collect()
}

pub fn remove_pool(zed_events: &mut state::ZedEvents, guid: u64) -> Result<libzfs_types::Pool> {
    zed_events
        .remove(&guid)
        .ok_or(Error::LibZfsError(libzfs_types::LibZfsError::PoolNotFound(
            None,
            Some(guid),
        )))
}

pub fn get_pool(zed_events: &mut state::ZedEvents, guid: u64) -> Result<&mut libzfs_types::Pool> {
    zed_events
        .get_mut(&guid)
        .ok_or(Error::LibZfsError(libzfs_types::LibZfsError::PoolNotFound(
            None,
            Some(guid),
        )))
}

fn update_prop(name: &str, value: &str, xs: &mut Vec<libzfs_types::ZProp>) {
    xs.retain(|z| z.name != name);

    xs.push(libzfs_types::ZProp {
        name: name.to_string(),
        value: value.to_string(),
    });
}

fn guid_to_u64(guid: zpool::Guid) -> Result<u64> {
    let guid: result::Result<u64, std::num::ParseIntError> = guid.into();
    Ok(guid?)
}

/// Mutably updates the Zed portion of the device map in response to `ZedCommand`s.
pub fn update_zed_events(
    mut zed_events: state::ZedEvents,
    cmd: PoolCommand,
) -> Result<state::ZedEvents> {
    tracing::debug!("Processing Pool command: {:?}", cmd);

    match cmd {
        PoolCommand::AddPools(pools) => Ok(into_zed_events(pools)),
        PoolCommand::AddPool(pool) | PoolCommand::UpdatePool(pool) => {
            Ok(zed_events.update(pool.guid, pool))
        }
        PoolCommand::RemovePool(guid) => {
            let guid = guid_to_u64(guid)?;

            remove_pool(&mut zed_events, guid)?;

            Ok(zed_events)
        }
        PoolCommand::AddDataset(guid, dataset) => {
            let guid = guid_to_u64(guid)?;

            let pool = get_pool(&mut zed_events, guid)?;

            pool.datasets.retain(|d| d.name != dataset.name);
            pool.datasets.push(dataset);

            Ok(zed_events)
        }
        PoolCommand::RemoveDataset(guid, zfs::Name(name)) => {
            let guid = guid_to_u64(guid)?;

            let pool = get_pool(&mut zed_events, guid)?;

            pool.datasets.retain(|d| d.name != name);

            Ok(zed_events)
        }
        PoolCommand::SetZpoolProp(guid, prop::Key(key), prop::Value(value)) => {
            let guid = guid_to_u64(guid)?;

            let pool = get_pool(&mut zed_events, guid)?;

            update_prop(&key, &value, &mut pool.props);

            Ok(zed_events)
        }
        PoolCommand::SetZfsProp(guid, zfs::Name(name), prop::Key(key), prop::Value(value)) => {
            let guid = guid_to_u64(guid)?;

            fn get_dataset_in_pool(
                pool: &mut libzfs_types::Pool,
                name: String,
            ) -> Result<&mut libzfs_types::Dataset> {
                pool.datasets
                    .iter_mut()
                    .find(|d| d.name == name)
                    .ok_or(Error::LibZfsError(libzfs_types::LibZfsError::ZfsNotFound(
                        name,
                    )))
            }

            let mut pool = get_pool(&mut zed_events, guid)?;
            let dataset = get_dataset_in_pool(&mut pool, name)?;

            update_prop(&key, &value, &mut dataset.props);

            Ok(zed_events)
        }
    }
}
