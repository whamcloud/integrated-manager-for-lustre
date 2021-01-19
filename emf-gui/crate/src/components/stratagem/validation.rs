// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{components::duration_picker, environment};

pub fn max_value_validation(ms: u64, unit: duration_picker::Unit) -> Option<String> {
    if ms > environment::MAX_SAFE_INTEGER {
        Some(format!(
            "Duration cannot be greater than {} {}",
            duration_picker::convert_ms_to_unit(unit, environment::MAX_SAFE_INTEGER),
            unit
        ))
    } else {
        None
    }
}

pub fn validate(
    scan_duration_picker: &mut duration_picker::Model,
    report_duration_picker: &mut duration_picker::Model,
    purge_duration_picker: &mut duration_picker::Model,
) {
    scan_duration_picker.validation_message = match scan_duration_picker.value_as_ms() {
        Some(ms) => {
            if ms < 1 {
                Some("Value must be a positive integer.".into())
            } else {
                max_value_validation(ms, scan_duration_picker.unit)
            }
        }
        None => Some("Please fill out this field.".into()),
    };

    validate_report_and_purge(report_duration_picker, purge_duration_picker);
}

pub fn validate_report_and_purge(
    report_duration_picker: &mut duration_picker::Model,
    purge_duration_picker: &mut duration_picker::Model,
) {
    let check = report_duration_picker
        .value
        .and_then(|r| purge_duration_picker.value.map(|p| r >= p))
        .unwrap_or(false);

    if check {
        report_duration_picker.validation_message = Some("Report duration must be less than Purge duration.".into());
    } else {
        report_duration_picker.validation_message = None;
    }
}
