// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{Msg, TooltipPlacement, TooltipSize};
use seed::{class, div, prelude::*, span};

/// A tooltip component
pub fn tooltip_component(
  message: &str,
  placement: &TooltipPlacement,
  size: &TooltipSize,
  more_classes: Option<Vec<&str>>,
) -> El<Msg> {
  let more_classes = match more_classes {
    Some(classes) => classes.join(" "),
    None => "".to_string(),
  };

  div![
    class![
      "tooltip inferno-tt",
      placement.into(),
      size.into(),
      more_classes.as_str()
    ],
    div![class!["tooltip-arrow"]],
    div![class!["tooltip-inner"], span![El::from_html(&message)]]
  ]
}
