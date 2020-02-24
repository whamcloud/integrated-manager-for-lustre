// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

static PREFIXES: [&str; 9] = ["", "K", "M", "G", "T", "P", "E", "Z", "Y"];

pub fn format_bytes(bytes: u64, precision: impl Into<Option<usize>>) -> String {
    let (s, exp) = normalize(bytes, precision, 1024);
    if exp > 0 {
        format!("{} {}iB", s, PREFIXES[exp as usize])
    } else {
        format!("{} B", s)
    }
}

pub fn format_number(num: u64, precision: impl Into<Option<usize>>) -> String {
    let (s, exp) = normalize(num, precision, 1000);
    if exp > 0 {
        format!("{}{}", s, PREFIXES[exp as usize])
    } else {
        s
    }
}

fn normalize(num: u64, precision: impl Into<Option<usize>>, base: u64) -> (String, u32) {
    let exp = ((num as f64).ln() / (base as f64).ln()).floor() as u32;
    let significand = num as f64 / base.pow(exp) as f64;

    let prcsn = if exp > 0 {
        precision.into().unwrap_or(1)
    } else {
        0
    };
    (format!("{:.*}", prcsn, significand), exp)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_format_bytes() {
        assert_eq!(format_bytes(1000, Some(0)), "1000 B");
        assert_eq!(format_bytes(1024, Some(3)), "1.000 KiB");
        assert_eq!(format_bytes(139_083_776, Some(1)), "132.6 MiB");
        assert_eq!(format_bytes(200_000, Some(1)), "195.3 KiB");
        assert_eq!(format_bytes(3_045_827_469, Some(3)), "2.837 GiB");
        assert_eq!(format_bytes(3_124_352, Some(3)), "2.980 MiB");
        assert_eq!(format_bytes(4326, Some(4)), "4.2246 KiB");
        assert_eq!(format_bytes(432_303_020_202, Some(3)), "402.614 GiB");
        assert_eq!(
            format_bytes(5_213_456_204_567_832_028, Some(3)),
            "4.522 EiB"
        );
        assert_eq!(format_bytes(5_323_330_102_372, Some(2)), "4.84 TiB");
        assert_eq!(format_bytes(84_567_942_345_572_238, Some(2)), "75.11 PiB");
    }

    #[test]
    fn test_format_number() {
        // TODO: assert_eq!(format_number(999999, Some(0)), "1M");
        assert_eq!(format_number(123, Some(0)), "123");
        assert_eq!(format_number(123, Some(3)), "123");
        assert_eq!(format_number(8007, Some(2)), "8.01K");
        assert_eq!(format_number(8007, Some(3)), "8.007K");
        assert_eq!(format_number(8007, Some(5)), "8.00700K");
        assert_eq!(format_number(800_700, Some(5)), "800.70000K");
        assert_eq!(format_number(8200, Some(0)), "8K");
        assert_eq!(format_number(8200, Some(1)), "8.2K");
        assert_eq!(format_number(8200, Some(3)), "8.200K");
        assert_eq!(format_number(8200, Some(5)), "8.20000K");
        assert_eq!(format_number(8_007_000, Some(5)), "8.00700M");
        assert_eq!(format_number(8_007_000_000, Some(1)), "8.0G");
        assert_eq!(format_number(8_007_000_000_000, Some(3)), "8.007T");
    }
}
