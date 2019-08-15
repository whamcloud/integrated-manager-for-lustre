// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use iml_wire_types::Command;
use prettytable::{Row, Table};
use spinners::{Spinner, Spinners};
use std::fmt::Display;

pub fn start_spinner(msg: &str) -> impl FnOnce(Option<String>) -> () {
    let grey = termion::color::Fg(termion::color::LightBlack);
    let reset = termion::color::Fg(termion::color::Reset);

    let s = format!("{}{}{}", grey, reset, msg);
    let s_len = s.len();

    let sp = Spinner::new(Spinners::Dots9, s);

    move |msg_opt| match msg_opt {
        Some(msg) => {
            sp.message(msg);
        }
        None => {
            sp.stop();
            print!("{}", termion::clear::CurrentLine);
            print!("{}", termion::cursor::Left(s_len as u16));
        }
    }
}

pub fn display_cmd_state(cmd: &Command) {
    if cmd.errored {
        display_error(format!("{} errored", cmd.message));
    } else if cmd.cancelled {
        println!("🚫 {} cancelled", cmd.message);
    } else if cmd.complete {
        display_success(format!("{} successful", cmd.message));
    }
}

pub fn display_success(message: impl Display) {
    let green = termion::color::Fg(termion::color::Green);
    let reset = termion::color::Fg(termion::color::Reset);

    println!("{}✔{} {}", green, reset, message);
}

pub fn display_error(message: impl Display) {
    let red = termion::color::Fg(termion::color::Red);
    let reset = termion::color::Fg(termion::color::Reset);

    println!("{}✗{} {}", red, reset, message);
}

pub fn generate_table<Rows, R>(columns: &[&str], rows: Rows) -> Table
where
    R: IntoIterator,
    R::Item: ToString,
    Rows: IntoIterator<Item = R>,
{
    let mut table = Table::new();

    table.add_row(Row::from(columns));

    for r in rows {
        table.add_row(Row::from(r));
    }

    table
}
