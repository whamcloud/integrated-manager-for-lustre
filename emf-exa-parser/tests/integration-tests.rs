// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use emf_exa_parser::config::ExascalerConfiguration;
use insta::{assert_json_snapshot, Settings};

#[test]
fn parse_exascaler_conf_from_file_test() {
    let json = include_str!("fixtures/exascaler.json");
    let exa: ExascalerConfiguration = serde_json::from_str(json).unwrap();
    let mut settings = Settings::new();
    settings.set_sort_maps(true);
    settings.bind(|| assert_json_snapshot!(exa));
}

#[test]
fn parse_exascaler_conf_from_file_test_ai400x() {
    let json = include_str!("fixtures/exascaler_ai400x.json");
    let exa: ExascalerConfiguration = serde_json::from_str(json).unwrap();
    let mut settings = Settings::new();
    settings.set_sort_maps(true);
    settings.bind(|| assert_json_snapshot!(exa));
}

#[test]
fn parse_exascaler_conf_from_file_test_zpool() {
    let json = include_str!("fixtures/exascaler_zpool.json");
    let exa: ExascalerConfiguration = serde_json::from_str(json).unwrap();
    let mut settings = Settings::new();
    settings.set_sort_maps(true);
    settings.bind(|| assert_json_snapshot!(exa));
}

#[test]
fn parse_exascaler_conf_from_file_test_bonded() {
    let json = include_str!("fixtures/exascaler_es7k_with_extMDS.json");
    let exa: ExascalerConfiguration = serde_json::from_str(json).unwrap();
    let mut settings = Settings::new();
    settings.set_sort_maps(true);
    settings.bind(|| assert_json_snapshot!(exa));
}
