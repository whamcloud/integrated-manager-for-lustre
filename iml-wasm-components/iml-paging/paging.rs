// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use bootstrap_components::{bs_button, bs_dropdown};
use iml_utils::WatchState;
use seed::{a, class, div, i, li, prelude::*, small, style};

pub struct Paging {
    pub limit: usize,
    pub total: usize,
    offset: usize,
    pub dropdown: WatchState,
}

pub const ROW_OPTS: [usize; 4] = [10, 25, 50, 100];

impl Default for Paging {
    fn default() -> Self {
        Paging {
            limit: ROW_OPTS[0],
            total: 0,
            offset: 0,
            dropdown: Default::default(),
        }
    }
}

impl Paging {
    fn has_more(&self) -> bool {
        self.limit + self.offset < self.total
    }
    fn has_less(&self) -> bool {
        self.offset != 0
    }
    pub fn offset(&self) -> usize {
        self.offset
    }
    pub fn end(&self) -> usize {
        std::cmp::min(self.offset + self.limit, self.total)
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
pub enum PagingMsg {
    Next,
    Prev,
    Dropdown(WatchState),
    Limit(usize),
}

pub fn page_selection(open: bool, rows: usize) -> El<PagingMsg> {
    let mut btn = bs_button::btn(
        class![bs_dropdown::DROPDOWN_TOGGLE, bs_button::EXTRASMALL],
        vec![
            El::new_text(&rows.to_string()),
            i![class!["fa", "fa-fw", "fa-caret-up", "icon-caret-up"]],
        ],
    );

    btn.listeners.push(mouse_ev(Ev::Click, |_| {
        PagingMsg::Dropdown(WatchState::Watching)
    }));

    bs_dropdown::wrapper(
        class!["dropup"],
        open,
        vec![
            btn,
            bs_dropdown::menu(
                ROW_OPTS
                    .iter()
                    .map(|x| {
                        li![
                            a![x.to_string()],
                            simple_ev(Ev::Click, PagingMsg::Limit(*x))
                        ]
                    })
                    .collect(),
            ),
        ],
    )
    .add_style("display".into(), "inline-block".into())
}

pub fn update_paging(msg: PagingMsg, p: &mut Paging) {
    match msg {
        PagingMsg::Next => {
            p.next_page();
        }
        PagingMsg::Prev => {
            p.prev_page();
        }
        PagingMsg::Dropdown(state) => {
            p.dropdown = state;
        }
        PagingMsg::Limit(limit) => {
            p.limit = limit;
        }
    }
}

pub fn paging(p: &Paging) -> El<PagingMsg> {
    div![
        style! {"display" => "grid", "grid-template-columns" => "75% 15% 10%"},
        div![
            style! { "align-self" => "center", "justify-self" => "end" },
            small!["Rows per page:"],
            page_selection(p.dropdown.is_open(), p.limit),
        ],
        small![
            style! { "align-self" => "center", "justify-self" => "center" },
            &format!("{} - {} of {}", p.offset() + 1, p.end(), p.total)
        ],
        div![
            style! { "align-self" => "center", "justify-self" => "center" },
            a![
                class![
                    bs_button::BTN,
                    bs_button::BTN_LINK,
                    bs_button::EXTRASMALL,
                    if p.has_less() {
                        ""
                    } else {
                        bootstrap_components::DISABLED
                    }
                ],
                simple_ev(Ev::Click, PagingMsg::Prev),
                i![class!["fas fa-chevron-left"]]
            ],
            a![
                class![
                    bs_button::BTN,
                    bs_button::BTN_LINK,
                    bs_button::EXTRASMALL,
                    if p.has_more() {
                        ""
                    } else {
                        bootstrap_components::DISABLED
                    }
                ],
                simple_ev(Ev::Click, PagingMsg::Next),
                i![class!["fas fa-chevron-right"]]
            ]
        ]
    ]
}
