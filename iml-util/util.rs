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
