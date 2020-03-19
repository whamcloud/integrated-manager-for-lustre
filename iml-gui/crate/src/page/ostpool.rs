use seed::prelude::*;

#[derive(Clone, Debug)]
pub enum Msg {}

pub struct Model {
    pub id: u32,
}

pub fn view(_model: &Model) -> impl View<Msg> {
    seed::empty()
}
