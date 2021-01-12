# emf-change

This crate provides a way to sort collections of items into buckets that can be upserted or deleted.
Users should implement the `Identifiable` trait and the `Changeable` trait for their items.
Once these are implemented, `get_changes` can be used to sort into `Upsertable` and `Deletable` collections.
