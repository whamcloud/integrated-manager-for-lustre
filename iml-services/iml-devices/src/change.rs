// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::{
    collections::{BTreeMap, BTreeSet},
    ops::Deref,
};

#[derive(Debug, PartialEq)]
pub enum Change<T> {
    Add(T),
    Update(T),
    Remove(T),
}

impl<T> Deref for Change<T> {
    type Target = T;

    fn deref(&self) -> &Self::Target {
        match self {
            Change::Add(x) | Change::Update(x) | Change::Remove(x) => x,
        }
    }
}

impl<T> Change<T> {
    pub fn map<R, F: Fn(&T) -> R>(&self, f: F) -> Change<R> {
        match self {
            Change::Add(x) => Change::Add(f(x)),
            Change::Update(x) => Change::Update(f(x)),
            Change::Remove(x) => Change::Remove(f(x)),
        }
    }
    pub fn is_add(&self) -> bool {
        match self {
            Change::Add(_) => true,
            _ => false,
        }
    }
}

pub fn get_changes_values<
    'a,
    'b,
    K: std::cmp::Eq + std::cmp::Ord + std::fmt::Debug,
    V: std::cmp::Eq + std::fmt::Debug,
>(
    old: &'b BTreeMap<&'a K, V>,
    new: &'b BTreeMap<&'a K, V>,
) -> Vec<Change<&'b V>> {
    let old_ids: BTreeSet<_> = old.keys().collect();
    let new_ids: BTreeSet<_> = new.keys().collect();

    let to_change = new_ids
        .intersection(&old_ids)
        .filter(|&&k| old.get(k) != new.get(k))
        .inspect(|&&k| tracing::debug!("not equal. old: {:?}, new {:?}", old.get(k), new.get(k)))
        .map(|&k| Change::Update(new.get(k).unwrap()));

    tracing::trace!("old ids: {:?}. new ids: {:?}", old_ids, new_ids);

    let to_remove = old_ids
        .difference(&new_ids)
        .map(|&k| Change::Remove(old.get(k).unwrap()));

    let to_add = new_ids
        .difference(&old_ids)
        .map(|&k| Change::Add(new.get(k).unwrap()));

    to_change.chain(to_remove).chain(to_add).collect()
}
pub fn get_changes<
    'a,
    'b,
    K: std::cmp::Eq + std::cmp::Ord + Clone,
    V: std::cmp::Eq + std::fmt::Debug,
>(
    old: &'b BTreeMap<&'a K, V>,
    new: &'b BTreeMap<&'a K, V>,
) -> Vec<Change<K>> {
    let old_ids: BTreeSet<_> = old.keys().collect();
    let new_ids: BTreeSet<_> = new.keys().collect();

    let to_change = new_ids
        .intersection(&old_ids)
        .filter(|&&k| old.get(k) != new.get(k))
        .inspect(|&&k| tracing::debug!("not equal. old: {:?}, new {:?}", old.get(k), new.get(k)))
        .map(|&&k| Change::Update(k.clone()));

    let to_remove = old_ids
        .difference(&new_ids)
        .map(|&&k| Change::Remove(k.clone()));

    let to_add = new_ids
        .difference(&old_ids)
        .map(|&&k| Change::Add(k.clone()));

    to_change.chain(to_remove).chain(to_add).collect()
}

#[cfg(test)]
mod test {
    use super::*;
    use insta::*;

    #[test]
    fn equal_maps_produce_no_changes() {
        let old: BTreeMap<isize, isize> = vec![(1, 1), (2, 2), (3, 3)].into_iter().collect();
        let new: BTreeMap<isize, isize> = vec![(1, 1), (2, 2), (3, 3)].into_iter().collect();
        let old = &old.iter().collect();
        let new = &new.iter().collect();

        let changes = get_changes_values(old, new);

        assert_debug_snapshot!("equal_maps_produce_no_changes", changes);
    }

    #[test]
    fn update_only_adds_updated_elements() {
        let old: BTreeMap<isize, isize> = vec![(1, 1), (2, 2), (3, 3)].into_iter().collect();
        let new: BTreeMap<isize, isize> = vec![(1, 1), (2, 2), (4, 4)].into_iter().collect();
        let old = &old.iter().collect();
        let new = &new.iter().collect();

        let changes = get_changes_values(old, new);

        assert_debug_snapshot!("update_only_adds_updated_elements", changes);
    }
}
