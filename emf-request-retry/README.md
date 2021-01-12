# Async Retry

## Typical usage

There are two functions to use: `retry_future` and `retry_future_gen`,
the former accepts a (mutable) reference to a RetryPolicy,
the latter accepts a general function `Fn(u32, E) -> RetryAction<E>`.

With the mutable policy you may implement some stateful strategy
with counters, randomization etc. The example of such policy is
`policy::ExponentialBackoffPolicy`.

## Running the example

```sh
cargo run --example demo-server-client
```
