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
        WatchState::Close
    }
}

impl WatchState {
    pub fn is_open(self) -> bool {
        match self {
            WatchState::Open => true,
            _ => false,
        }
    }

    pub fn is_watching(self) -> bool {
        match self {
            WatchState::Watching => true,
            _ => false,
        }
    }

    pub fn should_update(self) -> bool {
        self.is_watching() || self.is_open()
    }

    pub fn update(&mut self) {
        match self {
            WatchState::Close => {
                mem::replace(self, WatchState::Watching);
            }
            WatchState::Watching => {
                mem::replace(self, WatchState::Open);
            }
            WatchState::Open => {
                mem::replace(self, WatchState::Close);
            }
        }
    }
}
