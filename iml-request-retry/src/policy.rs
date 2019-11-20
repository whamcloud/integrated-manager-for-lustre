// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{RetryAction, RetryPolicy};
use rand::distributions::Distribution;
use rand::distributions::Uniform;
use rand::prelude::ThreadRng;
use rand::Rng;
use std::fmt::{self, Debug};
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
    #[allow[dead_code]]
    pub fn with_count_delay_rng(
        is_fatal_f: F,
        max_count: u32,
        initial_delay: Duration,
        rng: R,
        random_factor: f32,
    ) -> Self {
        ExponentialBackoffPolicy {
            rng,
            is_fatal_f,
            is_first_call: true,
            current_delay: initial_delay,
            randomized_delay: initial_delay,
            max_count,
            max_allowed_delay: Duration::from_secs(900),
            random_factor,
            multiplier: 1.5,
            _s: PhantomData,
        }
    }

    /// this is helper to implement `fn on_err(&mut self, request_no: u32, err: E)`
    /// [`on_err`]: RetryPolicy<E>::on_err
    /// [`on_err`]: ExponentialBackoffPolicy::on_err
    fn randomize(&mut self, current_seconds: f32) -> f32 {
        let delta = self.random_factor * current_seconds;
        let randomized_seconds = if delta > 0.0 {
            let range = Uniform::new(current_seconds - delta, current_seconds + delta);
            let seconds = range.sample(&mut self.rng);
            seconds
        } else {
            current_seconds
        };
        randomized_seconds
    }
}

impl<E, F> ExponentialBackoffPolicy<E, ThreadRng, F>
where
    E: Debug,
    F: Fn(&E) -> bool,
{
    #[allow[dead_code]]
    pub fn with_f(is_fatal_f: F) -> Self {
        let rng = rand::thread_rng();
        let random_factor = 0.5;
        let max_count = 16;
        let initial_delay = Duration::from_millis(500);
        ExponentialBackoffPolicy::with_count_delay_rng(
            is_fatal_f,
            max_count,
            initial_delay,
            rng,
            random_factor,
        )
    }

    #[allow[dead_code]]
    pub fn with_count(is_fatal_f: F, max_count: u32) -> Self {
        let rng = rand::thread_rng();
        let random_factor = 0.5;
        let initial_delay = Duration::from_millis(500);
        ExponentialBackoffPolicy::with_count_delay_rng(
            is_fatal_f,
            max_count,
            initial_delay,
            rng,
            random_factor,
        )
    }
}

impl<E, R, F> Debug for ExponentialBackoffPolicy<E, R, F>
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
                tracing::debug!(
                    "Request: {}, error:{:?} is fatal, returning it",
                    request_no,
                    err
                );
                RetryAction::ReturnError(err)
            } else {
                tracing::debug!(
                    "Request: {}, error:{:?} is not fatal, wait for {:?} before retry",
                    request_no,
                    err,
                    self.current_delay
                );
                RetryAction::WaitFor(self.randomized_delay)
            }
        } else {
            tracing::debug!(
                "Request: {}, error {:?}, reached maximum attempts {:?}",
                request_no,
                self.max_count,
                err
            );
            RetryAction::ReturnError(err)
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::SeedableRng;
    use rand_xorshift::XorShiftRng;

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
        let mut exp_policy = ExponentialBackoffPolicy::with_f(is_fatal);
        let errors = [
            Error::NonFatal,
            Error::NonFatal,
            Error::NonFatal,
            Error::NonFatal,
        ];

        let mut actions = vec![RetryAction::RetryNow; errors.len()];
        for i in 0..errors.len() {
            actions[i] = exp_policy.on_err(i as u32, errors[i].clone())
        }

        let intervals = [(0.25, 0.75), (0.375, 1.125), (0.562, 1.687), (0.8435, 2.53)];
        for i in 0..intervals.len() {
            let (l, u) = intervals[i];
            if let RetryAction::WaitFor(duration) = actions[i] {
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
        let seed = [16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1];
        let rng = XorShiftRng::from_seed(seed);
        let random_factor = 0.0;
        let max_count = 5;
        let delay = Duration::from_secs(1);
        let mut exp_policy = ExponentialBackoffPolicy::with_count_delay_rng(
            is_fatal_closure,
            max_count,
            delay,
            rng,
            random_factor,
        );
        let errors = [
            Error::NonFatal,
            Error::NonFatal,
            Error::NonFatal,
            Error::Fatal,
        ];
        let mut actions = vec![RetryAction::RetryNow; errors.len()];
        for i in 0..errors.len() {
            actions[i] = exp_policy.on_err(i as u32, errors[i].clone())
        }

        let r0 = exp_policy.on_err(0, Error::NonFatal);
        let r1 = exp_policy.on_err(1, Error::NonFatal);
        let r2 = exp_policy.on_err(3, Error::NonFatal);
        let r3 = exp_policy.on_err(2, Error::Fatal);

        assert_eq!(r0, RetryAction::WaitFor(Duration::from_secs_f32(1.0)));
        assert_eq!(r1, RetryAction::WaitFor(Duration::from_secs_f32(1.5)));
        assert_eq!(
            r2,
            RetryAction::WaitFor(Duration::from_secs_f32(2.249999872))
        );
        assert_eq!(r3, RetryAction::ReturnError(Error::Fatal));
    }

    #[test]
    fn exponential_policy_maximum_reached() {
        let mut exp_policy = ExponentialBackoffPolicy::with_count(|_| false, 8);
        // simulate the policy is called 10 times
        let errors = vec![Error::NonFatal; 10];
        let mut actions = vec![RetryAction::RetryNow; errors.len()];
        for i in 0..errors.len() {
            actions[i] = exp_policy.on_err(i as u32, errors[i].clone())
        }
        // first 8 steps waits and then failures
        for i in 0..actions.len() {
            match actions[i] {
                RetryAction::RetryNow => assert!(false),
                RetryAction::WaitFor(_) => assert!(i <= 7),
                RetryAction::ReturnError(Error::NonFatal) => assert!(7 < i),
                _ => assert!(false),
            }
        }
    }
}
