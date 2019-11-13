// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub trait Flatten<T> {
    fn flatten(self) -> Option<T>;
}

/// Implement flatten for the `Option` type.
/// See https://doc.rust-lang.org/std/option/enum.Option.html#method.flatten
/// for more information.
impl<T> Flatten<T> for Option<Option<T>> {
    fn flatten(self) -> Option<T> {
        self.unwrap_or(None)
    }
}

pub trait Pick<A, B> {
    fn fst(self) -> A;
    fn snd(self) -> B;
}

impl<A, B> Pick<A, B> for (A, B) {
    fn fst(self) -> A {
        self.0
    }
    fn snd(self) -> B {
        self.1
    }
}

impl<A, B, C> Pick<A, B> for (A, B, C) {
    fn fst(self) -> A {
        self.0
    }
    fn snd(self) -> B {
        self.1
    }
}

impl<A, B, C, D> Pick<A, B> for (A, B, C, D) {
    fn fst(self) -> A {
        self.0
    }
    fn snd(self) -> B {
        self.1
    }
}

impl<A, B, C, D, E> Pick<A, B> for (A, B, C, D, E) {
    fn fst(self) -> A {
        self.0
    }
    fn snd(self) -> B {
        self.1
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_option_of_some() {
        let x = Some(Some(7));
        assert_eq!(x.flatten(), Some(7));
    }

    #[test]
    fn test_option_of_none() {
        let x: Option<Option<i32>> = Some(None);
        assert_eq!(x.flatten(), None);
    }

    #[test]
    fn test_option_of_option_of_some() {
        let x = Some(Some(Some(7)));
        assert_eq!(x.flatten().flatten(), Some(7));
    }

    #[test]
    fn test_option_of_option_of_none() {
        let x: Option<Option<Option<u32>>> = Some(Some(None));
        assert_eq!(x.flatten().flatten(), None);
    }
}
