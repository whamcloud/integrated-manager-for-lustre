// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::{
    cmp::{Eq, Ord},
    collections::BTreeSet,
    fmt::Debug,
    iter::FromIterator,
};

pub trait Identifiable {
    type Id: Eq + Ord;

    fn id(&self) -> Self::Id;
}

pub trait Changeable: Eq + Ord + Debug {}

impl<T> Changeable for T where T: Eq + Ord + Debug {}

#[derive(Debug)]
pub struct Upserts<T: Changeable>(pub Vec<T>);

#[derive(Debug)]
pub struct Deletions<T: Changeable>(pub Vec<T>);

type Changes<'a, T> = (Option<Upserts<&'a T>>, Option<Deletions<&'a T>>);

pub trait GetChanges<T: Changeable + Identifiable> {
    /// Given new and old items, this method compares them and
    /// returns a tuple of `Upserts` and `Deletions`.
    fn get_changes<'a>(&'a self, old: &'a Self) -> Changes<'a, T>;
}

impl<T: Changeable + Identifiable> GetChanges<T> for Vec<T> {
    fn get_changes<'a>(&'a self, old: &'a Self) -> Changes<'a, T> {
        let new = BTreeSet::from_iter(self);
        let old = BTreeSet::from_iter(old);

        let to_upsert: Vec<&T> = new.difference(&old).copied().collect();

        let to_upsert = if to_upsert.is_empty() {
            None
        } else {
            Some(Upserts(to_upsert))
        };

        let new_ids: BTreeSet<<T as Identifiable>::Id> = new.iter().map(|x| x.id()).collect();
        let old_ids: BTreeSet<<T as Identifiable>::Id> = old.iter().map(|x| x.id()).collect();

        let changed: BTreeSet<_> = new_ids.intersection(&old_ids).collect();

        let to_remove: Vec<&T> = old
            .difference(&new)
            .filter(|x| {
                let id = x.id();

                changed.get(&id).is_none()
            })
            .copied()
            .collect();

        let to_remove = if to_remove.is_empty() {
            None
        } else {
            Some(Deletions(to_remove))
        };

        (to_upsert, to_remove)
    }
}
