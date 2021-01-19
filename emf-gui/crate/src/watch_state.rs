// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::mem;

/// An abstraction over a component being open / closed
/// or watching for a change. This is needed
/// due to the way seed handles window events.
#[derive(Debug, Copy, Clone, PartialEq, Eq)]
pub enum WatchState {
    Watching,
    Open,
    Close,
}

impl Default for WatchState {
    fn default() -> Self {
        Self::Close
    }
}

impl WatchState {
    pub fn is_open(self) -> bool {
        match self {
            Self::Open => true,
            _ => false,
        }
    }

    pub fn is_watching(self) -> bool {
        match self {
            Self::Watching => true,
            _ => false,
        }
    }

    pub fn should_update(self) -> bool {
        self.is_watching() || self.is_open()
    }

    pub fn update(&mut self) {
        match self {
            Self::Close => {
                let _ = mem::replace(self, Self::Watching);
            }
            Self::Watching => {
                let _ = mem::replace(self, Self::Open);
            }
            Self::Open => {
                let _ = mem::replace(self, Self::Close);
            }
        }
    }
}
