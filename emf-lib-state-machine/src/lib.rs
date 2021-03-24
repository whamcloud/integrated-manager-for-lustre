// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file

pub mod input_document;
pub mod state_schema;

use std::collections::HashMap;
use validator::{Validate, ValidationErrors};

pub(crate) trait ValidateAddon {
    fn validate(&self) -> Result<(), ValidationErrors>;
}

impl<T: Validate> ValidateAddon for HashMap<String, T> {
    fn validate(&self) -> Result<(), ValidationErrors> {
        for i in self.values() {
            i.validate()?
        }
        Ok(())
    }
}
