// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::cmp;

/// Format number given a precision, suffix and either 1000 or 1024 based Kilo
///
pub fn format(num: f64, precision: Option<usize>, suffix: &str, order2: bool) -> String {
    let units = ["", "K", "M", "G", "T", "P", "E", "Z", "Y"];

    let denominator = if order2 { 1024_f64 } else { 1000_f64 };
    let precision = precision.unwrap_or(1);

    let sign = if num < 0_f64 { "-" } else { "" };
    let num = num.abs();

    let pwr = (num.ln() / denominator.ln()).floor() as i32;
    let pwr = cmp::min(pwr, (units.len() - 1) as i32);
    let pwr = cmp::max(pwr, 0);

    let num = num / denominator.powi(pwr);

    let unit = units[pwr as usize];

    if !suffix.is_empty() {
        if order2 && !unit.is_empty() {
            format!("{}{:.*} {}i{}", sign, precision, num, unit, suffix)
        } else {
            format!("{}{:.*} {}{}", sign, precision, num, unit, suffix)
        }
    } else if !unit.is_empty() {
        format!("{}{:.*}{}", sign, precision, num, unit)
    } else {
        format!("{}{:.*}", sign, precision, num)
    }
}

pub fn format_bytes(bytes: f64, precision: impl Into<Option<usize>>) -> String {
    format(bytes, precision.into(), "B", true)
}

pub fn format_number(num: f64, precision: impl Into<Option<usize>>) -> String {
    format(num, precision.into(), "", false)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_format_bytes_success() {
        assert_eq!(format_bytes(320.0, Some(0)), "320 B");
        assert_eq!(format_bytes(200_000.0, Some(1)), "195.3 KiB");
        assert_eq!(format_bytes(3_124_352.0, Some(3)), "2.980 MiB");
        assert_eq!(format_bytes(432_303_020_202.0, Some(3)), "402.614 GiB");
        assert_eq!(format_bytes(5_323_330_102_372.0, Some(2)), "4.84 TiB");
        assert_eq!(format_bytes(1000.0, Some(0)), "1000 B");
        assert_eq!(format_bytes(1024.0, Some(3)), "1.000 KiB");
        assert_eq!(format_bytes(4326.0, Some(4)), "4.2246 KiB");
        assert_eq!(format_bytes(3_045_827_469.0, Some(3)), "2.837 GiB");
        assert_eq!(format_bytes(84_567_942_345_572_238.0, Some(2)), "75.11 PiB");
        assert_eq!(
            format_bytes(5_213_456_204_567_832_146_028.0, Some(3)),
            "4.416 ZiB"
        );
        assert_eq!(format_bytes(139_083_776.0, Some(1)), "132.6 MiB");
    }

    #[test]
    fn test_format_number_success() {
        assert_eq!(format_number(22.0, Some(10)), "22.0000000000");
        assert_eq!(format_number(22.3, Some(10)), "22.3000000000");
        assert_eq!(format_number(22.3, Some(2)), "22.30");
        assert_eq!(format_number(22.3, Some(1)), "22.3");
        assert_eq!(format_number(0.023, Some(5)), "0.02300");
        assert_eq!(format_number(0.023, Some(1)), "0.0");
        assert_eq!(format_number(8007.0, Some(5)), "8.00700K");
        assert_eq!(format_number(8007.0, Some(3)), "8.007K");
        assert_eq!(format_number(8007.0, Some(2)), "8.01K");
        assert_eq!(format_number(8_007_000.0, Some(5)), "8.00700M");
        assert_eq!(format_number(8_007_000_000.0, Some(1)), "8.0G");
        assert_eq!(format_number(8_007_000_000_000.0, Some(1)), "8.0T");
        assert_eq!(format_number(800_700.0, Some(5)), "800.70000K");
        assert_eq!(format_number(8200.0, Some(5)), "8.20000K");
        assert_eq!(format_number(8200.0, Some(3)), "8.200K");
        assert_eq!(format_number(8200.0, Some(1)), "8.2K");
        assert_eq!(format_number(8200.0, Some(0)), "8K");
    }
}
