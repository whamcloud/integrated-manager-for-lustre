// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

//! # Restrict
//!
//! This module provides utilities render a `Node` only if a given permission level is met.

use crate::SessionExt;
use emf_wire_types::{GroupType, Session};
use seed::{empty, prelude::*};

pub(crate) fn is_allowed<'a>(session: impl Into<Option<&'a Session>>, group: GroupType) -> bool {
    match session.into() {
        Some(s) => s.group_allowed(group),
        None => false,
    }
}

pub(crate) fn view<'a, T: 'static>(
    session: impl Into<Option<&'a Session>>,
    group: GroupType,
    child: Node<T>,
) -> Node<T> {
    if is_allowed(session, group) {
        child
    } else {
        empty![]
    }
}
