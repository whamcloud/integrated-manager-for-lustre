use crate::Msg;
use seed::prelude::*;

pub struct Model {
    pub id: u32,
}

pub fn view(_model: &Model) -> impl View<Msg> {
    seed::empty()
}
