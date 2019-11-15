use crate::{generated::css_classes::C, Model, Msg};
use seed::{prelude::*, *};

pub fn view(model: &Model) -> impl View<Msg> {
    div!["welcome to jobstats"]
}
