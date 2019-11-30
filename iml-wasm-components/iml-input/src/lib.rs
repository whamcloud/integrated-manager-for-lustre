use combine::stream::easy::{Error, Errors, Info};
use seed::{class, div, input, prelude::*};

use iml_tooltip::TooltipPlacement;

pub struct Model<T> {
    pub value: Result<T, Option<String>>,
    pub tooltip: iml_tooltip::Model,
}

impl<T> Default for Model<T> {
    fn default() -> Self {
        Self {
            value: Err(None),
            tooltip: iml_tooltip::Model {
                error_tooltip: true,
                open: true,
                placement: TooltipPlacement::Bottom,
                ..Default::default()
            },
        }
    }
}

#[derive(Clone)]
pub enum Msg {
    FlipTooltip,
    InputChanged(String),
}

pub type ParserFn<T> = fn(_: &str) -> Result<T, Errors<char, &str, usize>>;

fn format_err(err: &Errors<char, &str, usize>) -> String {
    let mut un = vec![];
    let mut ex = vec![];

    fn format_info(i: &Info<char, &str>) -> String {
        match i {
            Info::Token(t) => {
                if *t != '"' {
                    format!("\"{}\"", t)
                } else {
                    format!("{}", t)
                }
            }
            Info::Static(s) => String::from(*s),
            Info::Owned(s) => String::from(s),
            Info::Range(r) => String::from(*r),
        }
    }

    for x in &err.errors {
        match x {
            Error::Unexpected(i) => {
                un.push(format_info(i));
            }
            Error::Expected(i) => {
                ex.push(format_info(i));
            }
            _ => {}
        }
    }

    let mut s = format!("Unexpected {}", un.join(", "));
    if ex.len() > 0 {
        s.push_str(&format!(". Expecting {}", ex.join(", ")));
    }
    s
}

pub fn update<T>(msg: Msg, m: &mut Model<T>, parse: ParserFn<T>) {
    match msg {
        Msg::FlipTooltip => {
            m.tooltip.placement = match m.tooltip.placement {
                TooltipPlacement::Bottom => TooltipPlacement::Top,
                _ => TooltipPlacement::Bottom,
            }
        }
        Msg::InputChanged(txt) => {
            m.value = parse(&txt).map_err(|e| Some(format_err(&e)));
        }
    }
}

pub fn view<T>(m: &Model<T>) -> Node<Msg> {
    let input = input![
        class!["form-control"],
        input_ev(Ev::Input, Msg::InputChanged)
    ];

    let mut group = div![input, class!["input-group"]];

    if let Err(me) = &m.value {
        if let Some(e) = me {
            let mut tooltip = iml_tooltip::tooltip(&e, &m.tooltip);
            tooltip.add_listener(simple_ev(Ev::Click, Msg::FlipTooltip));
            group.add_child(tooltip);
            group.add_class("has-error");
        } else {
            group.add_class("has-warning");
        }
    } else {
        group.add_class("has-success");
    }

    group
}
