// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::uevent;

#[derive(Debug, PartialEq, serde::Serialize, serde::Deserialize)]
pub enum UdevCommand {
    Add(uevent::UEvent),
    Change(uevent::UEvent),
    Remove(uevent::UEvent),
}
