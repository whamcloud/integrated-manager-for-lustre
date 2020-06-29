# futures-failure

This crate adds a `context` method via a blanket impl for `Future` and `Stream`.

The return of `context` is coerced into an `Error` so no explicit coercion is needed.
This is similar to the `ResultExt` `context` method, but different in that `Error` is returned instead of
`Context<T>`.

Blanked impls can be imported as `use futures_failure::{FutureExt, StreamExt};`
