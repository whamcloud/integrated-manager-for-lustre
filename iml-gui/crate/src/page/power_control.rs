use crate::Model;
use seed::prelude::*;

#[derive(Clone)]
pub enum Msg {}

pub fn view(_model: &Model) -> impl View<Msg> {
    seed::empty()
}
