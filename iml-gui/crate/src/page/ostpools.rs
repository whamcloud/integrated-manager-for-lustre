use crate::Model;
use seed::prelude::*;

#[derive(Clone, Debug)]
pub enum Msg {}

pub fn view(_model: &Model) -> impl View<Msg> {
    seed::empty()
}
