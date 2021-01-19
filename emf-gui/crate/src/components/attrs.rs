// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

/**
 A module for common attributes.

 While CSS classes and other attributes should belong to respective components,
 sometimes they can be common among different components. For example, a
 "button" could be an `<a>` or a `<button>`.
*/
use crate::generated::css_classes::C;
use seed::{prelude::*, *};

/// Call this fn within the element wrapping the tooltip or popup (or both)
/// It will add the needed styles so the tooltip and popup will render
/// in the expected position and behaviour.
pub(crate) fn container() -> Attrs {
    class![C.relative, C.group]
}
