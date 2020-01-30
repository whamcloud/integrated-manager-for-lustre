//! # Restrict
//!
//! This module provides utilities render a `Node` only if a given permission level is met.

use crate::SessionExt;
use iml_wire_types::{GroupType, Session};
use seed::{empty, prelude::*};

pub(crate) fn view<'a, T: 'static>(
    session: impl Into<Option<&'a Session>>,
    group: GroupType,
    child: Node<T>,
) -> Node<T> {
    let session = match session.into() {
        Some(s) => s,
        None => return empty![],
    };

    if session.group_allowed(group) {
        child
    } else {
        empty![]
    }
}
