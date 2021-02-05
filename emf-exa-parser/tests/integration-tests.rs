// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use exa_parser::{parse_exascaler_conf_from_file, EXAParserError, ExascalerConfiguration};
use insta::{assert_json_snapshot, Settings};

#[tokio::test]
#[ignore]
async fn parse_exascaler_conf_from_file_test() -> Result<(), EXAParserError> {
    let exascaler_conf_file_path = "fixtures/exascaler.conf";
    let mut settings = Settings::new();
    settings.set_sort_maps(true);
    let exa: ExascalerConfiguration =
        parse_exascaler_conf_from_file(exascaler_conf_file_path).await?;
    settings.bind(|| assert_json_snapshot!(exa));
    Ok(())
}

#[tokio::test]
#[ignore]
async fn parse_exascaler_conf_from_file_test_ai400x() -> Result<(), EXAParserError> {
    let exascaler_conf_file_path = "fixtures/exascaler_ai400x.conf";
    let mut settings = Settings::new();
    settings.set_sort_maps(true);
    let exa: ExascalerConfiguration =
        parse_exascaler_conf_from_file(exascaler_conf_file_path).await?;
    settings.bind(|| assert_json_snapshot!(exa));
    Ok(())
}

#[tokio::test]
#[ignore]
async fn parse_exascaler_conf_from_file_test_zpool() -> Result<(), EXAParserError> {
    let exascaler_conf_file_path = "fixtures/exascaler_zpool.conf";
    let mut settings = Settings::new();
    settings.set_sort_maps(true);
    let exa: ExascalerConfiguration =
        parse_exascaler_conf_from_file(exascaler_conf_file_path).await?;
    settings.bind(|| assert_json_snapshot!(exa));
    Ok(())
}

#[tokio::test]
#[ignore]
async fn parse_exascaler_conf_from_file_test_not_existing_file() -> Result<(), EXAParserError> {
    let exascaler_conf_file_path = "exascaler.conf.unknown";
    let mut settings = Settings::new();
    settings.set_sort_maps(true);
    let exa = parse_exascaler_conf_from_file(exascaler_conf_file_path).await;
    assert!(exa.is_err());
    Ok(())
}

#[tokio::test]
#[ignore]
async fn parse_exascaler_conf_from_file_test_existing_file_notvalid() -> Result<(), EXAParserError>
{
    let exascaler_conf_file_path = "fixtures/exascaler_notvalid.conf";
    let mut settings = Settings::new();
    settings.set_sort_maps(true);
    let exa = parse_exascaler_conf_from_file(exascaler_conf_file_path).await;
    assert!(exa.is_err());
    Ok(())
}
