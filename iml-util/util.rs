// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

pub trait Flatten<T> {
    fn flatten(self) -> Option<T>;
}

impl<T> Flatten<T> for Option<Option<T>> {
    fn flatten(self) -> Option<T> {
        self.unwrap_or(None)
    }
}

impl<T> Flatten<T> for Option<Option<Option<T>>> {
    fn flatten(self) -> Option<T> {
        self.unwrap_or(None).unwrap_or(None)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_option_of_Some() {
        let x = Some(Some(7));
        assert_eq!(x.flatten(), Some(7));
    }

    #[test]
    fn test_option_of_None() {
        let x = Some(Some(None));
        assert_eq!(x.flatten(), None);
    }

    #[test]
    fn test_option_of_option_of_some() {
        let x = Some(Some(Some(7)));
        assert_eq!(x.flatten(), Some(7));
    }

    #[test]
    fn test_option_of_option_of_None() {
        let x = Some(Some(None));
        assert_eq!(x.flatten(), None);
    }
}
