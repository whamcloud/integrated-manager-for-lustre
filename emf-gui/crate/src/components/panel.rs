// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::generated::css_classes::C;
use seed::{prelude::*, *};

pub fn view<T>(heading: impl View<T>, body: impl View<T>) -> Node<T> {
    div![
        class![C.bg_white],
        div![class![C.px_6, C.bg_gray_200], heading.els()],
        div![body.els()]
    ]
}
