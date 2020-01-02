use crate::WatchState;
use std::ops::Range;

#[derive(Debug)]
pub struct Model {
    pub limit: usize,
    pub total: usize,
    offset: usize,
    pub dropdown: WatchState,
}

pub const ROW_OPTS: [usize; 4] = [10, 25, 50, 100];

impl Default for Model {
    fn default() -> Self {
        Model {
            limit: ROW_OPTS[0],
            total: 0,
            offset: 0,
            dropdown: Default::default(),
        }
    }
}

pub fn slice_page<'a, T>(xs: &'a [T], model: &Model) -> &'a [T] {
    &xs[model.range()]
}

impl Model {
    pub fn new(total: usize) -> Self {
        Model {
            total,
            ..Model::default()
        }
    }

    pub const fn has_more(&self) -> bool {
        self.limit + self.offset < self.total
    }

    pub const fn has_less(&self) -> bool {
        self.offset != 0
    }

    pub fn has_pages(&self) -> bool {
        self.has_more() || self.has_less()
    }

    pub const fn offset(&self) -> usize {
        self.offset
    }

    pub fn end(&self) -> usize {
        std::cmp::min(self.offset + self.limit, self.total)
    }

    pub fn range(&self) -> Range<usize> {
        self.offset()..self.end()
    }

    pub fn prev_page(&mut self) {
        self.offset = if self.limit > self.offset {
            0
        } else {
            self.offset - self.limit
        };
    }

    pub fn next_page(&mut self) {
        self.offset = std::cmp::min(self.offset + self.limit, self.total - 1);
    }
}

#[derive(Clone)]
pub enum Msg {
    Next,
    Prev,
    Dropdown(WatchState),
    Limit(usize),
}

pub fn update(msg: Msg, model: &mut Model) {
    match msg {
        Msg::Next => {
            model.next_page();
        }
        Msg::Prev => {
            model.prev_page();
        }
        Msg::Dropdown(state) => {
            model.dropdown = state;
        }
        Msg::Limit(limit) => {
            model.limit = limit;
        }
    }
}
