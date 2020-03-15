use seed::prelude::*;

#[derive(Clone)]
pub enum Msg {}

pub struct Model {
    pub id: u32,
}

pub fn view(_model: &Model) -> impl View<Msg> {
    seed::empty()
}
