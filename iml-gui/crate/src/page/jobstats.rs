use crate::{Model, Msg};
use seed::{prelude::*, *};

pub fn view(_model: &Model) -> impl View<Msg> {
    div!["welcome to jobstats"]
}
