// Copyright (c) 2021 DDN. All rights reserved.
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

pub type Changes<'a, T> = (Option<Upserts<&'a T>>, Option<Deletions<&'a T>>);

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

#[cfg(test)]
mod tests {
    use super::*;
    use std::cmp::Ordering;

    #[derive(Clone, Eq, Ord, Debug)]
    struct Item {
        col1: String,
        col2: String,
        age: i32,
        amount: i32,
    }

    impl PartialEq for Item {
        fn eq(&self, other: &Self) -> bool {
            self.col1 == other.col1 && self.col2 == other.col2
        }
    }

    impl PartialOrd for Item {
        fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
            Some(self.age.cmp(&other.age))
        }
    }

    impl Identifiable for Item {
        type Id = String;

        fn id(&self) -> Self::Id {
            format!("{}.{}", self.col1, self.col2)
        }
    }

    #[test]
    fn test_get_changes() {
        let items1 = vec![
            Item {
                col1: "mickey".into(),
                col2: "mouse".into(),
                age: 16,
                amount: 27,
            },
            Item {
                col1: "minnie".into(),
                col2: "mouse".into(),
                age: 17,
                amount: 32,
            },
            Item {
                col1: "All your base".into(),
                col2: "Are belong to us".into(),
                age: 54,
                amount: 0,
            },
        ]
        .into_iter()
        .collect::<Vec<Item>>();

        let items2 = vec![
            Item {
                col1: "mickey".into(),
                col2: "mouse".into(),
                age: 16,
                amount: 27,
            },
            Item {
                col1: "minnie".into(),
                col2: "mouse".into(),
                age: 23,
                amount: 32,
            },
            Item {
                col1: "donald".into(),
                col2: "duck".into(),
                age: 7,
                amount: 18,
            },
        ]
        .into_iter()
        .collect::<Vec<Item>>();

        let (upserts, deletions) = items1.get_changes(&items2);

        assert_eq!(
            upserts
                .unwrap()
                .0
                .into_iter()
                .cloned()
                .collect::<Vec<Item>>(),
            vec![
                Item {
                    col1: "All your base".into(),
                    col2: "Are belong to us".into(),
                    age: 54,
                    amount: 0,
                },
                Item {
                    col1: "minnie".into(),
                    col2: "mouse".into(),
                    age: 17,
                    amount: 32,
                }
            ]
        );

        assert_eq!(
            deletions
                .unwrap()
                .0
                .into_iter()
                .cloned()
                .collect::<Vec<Item>>(),
            vec![Item {
                col1: "donald".into(),
                col2: "duck".into(),
                age: 7,
                amount: 18,
            }]
        );
    }
}
