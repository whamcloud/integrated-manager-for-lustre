// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{RetryAction, RetryPolicy};
use rand::distributions::Distribution;
use rand::distributions::Uniform;
use rand::Rng;
use rand_xoshiro::rand_core::SeedableRng;
use rand_xoshiro::Xoshiro256PlusPlus;
use std::fmt;
use std::fmt::Debug;
use std::marker::PhantomData;
use std::time::Duration;

///
/// Adaptation of [ExponentialBackOff from Google Http Client](https://github.com/googleapis/google-http-java-client/blob/master/google-http-client/src/main/java/com/google/api/client/util/ExponentialBackOff.java)
///```
/// // request_no  delay_in_seconds  randomized_interval
/// //  0          0.5               [0.25,   0.75]
/// //  1          0.75              [0.375,  1.125]
/// //  2          1.125             [0.562,  1.687]
/// //  3          1.687             [0.8435, 2.53]
/// //  4          2.53              [1.265,  3.795]
/// //  5          3.795             [1.897,  5.692]
/// //  6          5.692             [2.846,  8.538]
/// //  7          8.538             [4.269, 12.807]
/// //  8         12.807             [6.403, 19.210]
/// //  9         19.210             ...
///```
///
/// `is_fatal_f` is a function, that detects, if an error fatal or not. If error is fatal,
/// then there is no reason to make an additional attempts. Usually, for HTTP
/// ```no_run
/// use tokio::io;
///
/// let is_fatal_f = |err: &io::Error| match err.kind() {
///     io::ErrorKind::Interrupted
///     | io::ErrorKind::ConnectionReset
///     | io::ErrorKind::ConnectionAborted
///     | io::ErrorKind::NotConnected
///     | io::ErrorKind::BrokenPipe => false,
///     _ => true, // e.g. io::ErrorKind::PermissionDenied
/// };
/// ```
pub struct ExponentialBackoffPolicy<E: Debug, R: Rng, F: Fn(&E) -> bool> {
    pub rng: R,
    pub is_fatal_f: F,
    pub is_first_call: bool,
    pub current_delay: Duration,
    pub randomized_delay: Duration,
    pub max_count: u32,
    pub max_allowed_delay: Duration,
    pub random_factor: f32,
    pub multiplier: f32,
    pub _s: PhantomData<E>,
}

impl<E, R, F> ExponentialBackoffPolicy<E, R, F>
where
    E: Debug,
    R: Rng,
    F: for<'r> Fn(&'r E) -> bool,
{
    pub fn new(is_fatal_f: F, rng: R) -> Self {
        Self {
            rng,
            is_fatal_f,
            is_first_call: true,
            current_delay: Duration::from_millis(500),
            randomized_delay: Duration::from_millis(500),
            max_count: 16,
            max_allowed_delay: Duration::from_secs(900),
            random_factor: 0.5,
            multiplier: 1.5,
            _s: PhantomData,
        }
    }

    /// this is helper to implement `fn on_err(&mut self, request_no: u32, err: E)`
    /// [`on_err`]: RetryPolicy<E>::on_err
    /// [`on_err`]: ExponentialBackoffPolicy::on_err
    fn randomize(&mut self, current_seconds: f32) -> f32 {
        let delta = self.random_factor * current_seconds;
        if delta > 0.0 {
            let range = Uniform::new(current_seconds - delta, current_seconds + delta);
            // return seconds randomized around current_seconds
            range.sample(&mut self.rng)
        } else {
            current_seconds
        }
    }
}

impl<E, R, F> fmt::Debug for ExponentialBackoffPolicy<E, R, F>
where
    E: Debug,
    R: Rng,
    F: Fn(&E) -> bool,
{
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> Result<(), fmt::Error> {
        f.write_str("ExponentialBackoffPolicy {")?;
        f.write_fmt(format_args!("  is_first_call: {:?}", self.is_first_call))?;
        f.write_fmt(format_args!("  current_delay: {:?}", self.current_delay))?;
        f.write_fmt(format_args!(
            "  randomized_delay: {:?}",
            self.randomized_delay
        ))?;
        f.write_fmt(format_args!("  max_count: {}", self.max_count))?;
        f.write_fmt(format_args!(
            "  max_allowed_delay: {:?}",
            self.max_allowed_delay
        ))?;
        f.write_fmt(format_args!("  random_factor: {}", self.random_factor))?;
        f.write_fmt(format_args!("  multiplier: {}", self.multiplier))?;
        f.write_str("}")?;
        Ok(())
    }
}

impl<E, R, F> RetryPolicy<E> for ExponentialBackoffPolicy<E, R, F>
where
    E: Debug,
    R: Rng,
    F: Fn(&E) -> bool,
{
    fn on_err(&mut self, request_no: u32, err: E) -> RetryAction<E> {
        if request_no < self.max_count {
            let max_allowed_seconds = self.max_allowed_delay.as_secs_f32();
            let current_seconds = f32::min(self.current_delay.as_secs_f32(), max_allowed_seconds);

            // this check is needed to return the initial_delay for the first time
            // only current_delay is multiplied,
            // the randomization is being done for the current_delay independently
            let current_seconds = if self.is_first_call {
                self.is_first_call = false;
                current_seconds
            } else {
                current_seconds * self.multiplier
            };

            let randomized_seconds =
                ExponentialBackoffPolicy::<E, R, F>::randomize(self, current_seconds);
            self.current_delay = Duration::from_secs_f32(current_seconds);
            self.randomized_delay = Duration::from_secs_f32(randomized_seconds);

            if (self.is_fatal_f)(&err) {
                RetryAction::ReturnError(err)
            } else {
                RetryAction::WaitFor(self.randomized_delay)
            }
        } else {
            RetryAction::ReturnError(err)
        }
    }
}

/// The builder for `ExponentialBackoffPolicy`. Typical usage:
///
/// ```no_run
/// use emf_request_retry::policy::{ExponentialBackoffPolicyBuilder, exponential_backoff_policy_builder};
/// use std::time::Duration;
/// use std::io;
/// use rand::thread_rng;
///
/// let policy = exponential_backoff_policy_builder::<io::Error>()
///     .max_count(4)
///     .initial_delay(Duration::from_millis(100))
///     .random_factor(0.0)
///     .multiplier(2.0)
///     .build();
///
/// // or
///
/// let rng = thread_rng();
/// let is_fatal_f = |err: &io::Error| match err.kind() {
///     io::ErrorKind::Interrupted
///     | io::ErrorKind::ConnectionReset
///     | io::ErrorKind::ConnectionAborted
///     | io::ErrorKind::NotConnected
///     | io::ErrorKind::BrokenPipe => false,
///     _ => true, // e.g. io::ErrorKind::PermissionDenied
/// };
/// let policy = ExponentialBackoffPolicyBuilder::new(is_fatal_f, rng)
///     .max_count(4)
///     .initial_delay(Duration::from_millis(100))
///     .random_factor(0.0)
///     .multiplier(2.0)
///     .build();
/// ```
pub struct ExponentialBackoffPolicyBuilder<E: Debug, R: Rng, F: Fn(&E) -> bool> {
    pub rng: R,
    pub is_fatal_f: F,
    pub initial_delay: Option<Duration>,
    pub max_count: Option<u32>,
    pub random_factor: Option<f32>,
    pub multiplier: Option<f32>,
    pub _s: PhantomData<E>,
}

// `Xoshiro256PlusPlus` is pure, has all the internal state inside, so it is safe to be sent.
// `Fn(&'r E) -> bool` is safe to be sent, since it accepts a shared reference.
unsafe impl<E, F> Send for ExponentialBackoffPolicy<E, Xoshiro256PlusPlus, F>
where
    E: Debug + Send,
    F: for<'r> Fn(&'r E) -> bool,
{
}

/// The policy uses `xoshiro256++`, the `xoshiro256++` algorithm is not suitable for
/// cryptographic purposes, but is very fast and has excellent statistical properties.
/// Uses `seed` as the current seconds since Epoch.
pub fn exponential_backoff_policy_builder<E>(
) -> ExponentialBackoffPolicyBuilder<E, Xoshiro256PlusPlus, &'static dyn Fn(&E) -> bool>
where
    E: Debug,
{
    let seed = std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_else(|_| Duration::from_secs(0))
        .as_secs();
    exponential_backoff_policy_builder_with_seed(seed)
}

/// The policy uses `xoshiro256++`, the `xoshiro256++` algorithm is not suitable for
/// cryptographic purposes, but is very fast and has excellent statistical properties.
pub fn exponential_backoff_policy_builder_with_seed<E>(
    seed: u64,
) -> ExponentialBackoffPolicyBuilder<E, Xoshiro256PlusPlus, &'static dyn Fn(&E) -> bool>
where
    E: Debug,
{
    let rng = Xoshiro256PlusPlus::seed_from_u64(seed);
    let is_fatal_f = &|_: &E| false; // all errors are not fatal, always retry
    ExponentialBackoffPolicyBuilder {
        rng,
        is_fatal_f,
        initial_delay: None,
        max_count: None,
        random_factor: None,
        multiplier: None,
        _s: PhantomData,
    }
}

impl<E, R, F> ExponentialBackoffPolicyBuilder<E, R, F>
where
    E: Debug,
    R: Rng,
    F: for<'r> Fn(&'r E) -> bool,
{
    pub fn new(is_fatal_f: F, rng: R) -> Self {
        Self {
            rng,
            is_fatal_f,
            initial_delay: None,
            max_count: None,
            random_factor: None,
            multiplier: None,
            _s: PhantomData,
        }
    }
    pub fn initial_delay(mut self, initial_delay: Duration) -> Self {
        self.initial_delay = Some(initial_delay);
        self
    }
    pub fn max_count(mut self, max_count: u32) -> Self {
        self.max_count = Some(max_count);
        self
    }
    pub fn random_factor(mut self, random_factor: f32) -> Self {
        self.random_factor = Some(random_factor);
        self
    }
    pub fn multiplier(mut self, multiplier: f32) -> Self {
        self.multiplier = Some(multiplier);
        self
    }
    pub fn build(self) -> ExponentialBackoffPolicy<E, R, F> {
        let mut policy = ExponentialBackoffPolicy::new(self.is_fatal_f, self.rng);
        if let Some(initial_delay) = self.initial_delay {
            policy.current_delay = initial_delay;
            policy.randomized_delay = initial_delay;
        }
        if let Some(max_count) = self.max_count {
            policy.max_count = max_count;
        }
        if let Some(random_factor) = self.random_factor {
            policy.random_factor = random_factor;
        }
        if let Some(multiplier) = self.multiplier {
            policy.multiplier = multiplier;
        }

        policy
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::RetryAction::{RetryNow, ReturnError, WaitFor};
    use rand::SeedableRng;
    use rand_xoshiro::Xoshiro256PlusPlus;

    #[derive(Debug, Clone, PartialEq)]
    enum Error {
        Fatal,
        NonFatal,
    }

    fn is_fatal(err: &Error) -> bool {
        match err {
            Error::Fatal => true,
            Error::NonFatal => false,
        }
    }

    #[test]
    fn exponential_policy_check_intervals() {
        let rng = Xoshiro256PlusPlus::seed_from_u64(256);
        let mut exp_policy = ExponentialBackoffPolicyBuilder::new(is_fatal, rng).build();
        let errors = [
            Error::NonFatal,
            Error::NonFatal,
            Error::NonFatal,
            Error::NonFatal,
        ];

        let mut actions = vec![RetryNow; errors.len()];
        for i in 0..errors.len() {
            actions[i] = exp_policy.on_err(i as u32, errors[i].clone())
        }

        let intervals = [(0.25, 0.75), (0.375, 1.125), (0.562, 1.687), (0.8435, 2.53)];
        for i in 0..intervals.len() {
            let (l, u) = intervals[i];
            if let WaitFor(duration) = actions[i] {
                assert!(l <= duration.as_secs_f32());
                assert!(duration.as_secs_f32() <= u);
            } else {
                assert!(false)
            }
        }
    }

    #[test]
    fn exponential_policy_with_custom_rng() {
        let is_fatal_closure = |e: &Error| match e {
            Error::Fatal => true,
            Error::NonFatal => false,
        };
        let rng = Xoshiro256PlusPlus::seed_from_u64(256);
        let mut exp_policy = ExponentialBackoffPolicyBuilder::new(is_fatal_closure, rng)
            .max_count(5)
            .initial_delay(Duration::from_secs(1))
            .random_factor(0.0)
            .build();
        let errors = [
            Error::NonFatal,
            Error::NonFatal,
            Error::NonFatal,
            Error::Fatal,
        ];
        let mut actions = vec![RetryNow; errors.len()];
        for i in 0..errors.len() {
            actions[i] = exp_policy.on_err(i as u32, errors[i].clone())
        }

        assert_eq!(actions[0], WaitFor(Duration::from_secs_f32(1.0)));
        assert_eq!(actions[1], WaitFor(Duration::from_secs_f32(1.5)));
        assert_eq!(actions[2], WaitFor(Duration::from_secs_f32(2.249_999_8)));
        assert_eq!(actions[3], ReturnError(Error::Fatal));
    }

    #[test]
    fn exponential_policy_maximum_reached() {
        let rng = Xoshiro256PlusPlus::seed_from_u64(42);
        let mut exp_policy = ExponentialBackoffPolicyBuilder::new(|_| false, rng)
            .max_count(8)
            .build();
        // simulate the policy is called 10 times
        let errors = vec![Error::NonFatal; 10];
        let mut actions = vec![RetryNow; errors.len()];
        for i in 0..errors.len() {
            actions[i] = exp_policy.on_err(i as u32, errors[i].clone())
        }
        // first 8 steps waits and then failures
        for i in 0..actions.len() {
            match actions[i] {
                RetryNow => assert!(false),
                WaitFor(_) => assert!(i <= 7),
                ReturnError(Error::NonFatal) => assert!(7 < i),
                _ => assert!(false),
            }
        }
    }
}
