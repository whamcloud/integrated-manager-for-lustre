// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::Record;

#[derive(serde::Deserialize, serde::Serialize, Debug, PartialEq, Clone)]
pub struct MdtConfParams {
    #[serde(rename = "lov.qos_prio_free")]
    lov_qos_prio_free: Option<String>,
    #[serde(rename = "lov.qos_threshold_rr")]
    lov_qos_threshold_rr: Option<String>,
    #[serde(rename = "lov.stripecount")]
    lov_stripecount: Option<String>,
    #[serde(rename = "lov.stripesize")]
    lov_stripesize: Option<String>,
    #[serde(rename = "mdt.MDS.mds.threads_max")]
    mdt_mds_mds_threads_max: Option<String>,
    #[serde(rename = "mdt.MDS.mds.threads_min")]
    mdt_mds_mds_threads_min: Option<String>,
    #[serde(rename = "mdt.MDS.mds_readpage.threads_max")]
    mdt_mds_mds_readpage_threads_max: Option<String>,
    #[serde(rename = "mdt.MDS.mds_readpage.threads_min")]
    mdt_mds_mds_readpage_threads_min: Option<String>,
    #[serde(rename = "mdt.MDS.mds_setattr.threads_max")]
    mdt_mds_mds_setattr_threads_max: Option<String>,
    #[serde(rename = "mdt.MDS.mds_setattr.threads_min")]
    mdt_mds_mds_setattr_threads_min: Option<String>,
    #[serde(rename = "mdt.hsm_control")]
    mdt_hsm_control: Option<String>,
}

/// Mdt is part of the HsmControlParam
#[derive(serde::Deserialize, serde::Serialize, Debug, PartialEq, Clone)]
pub struct Mdt {
    pub id: String,
    pub kind: String,
    pub resource: String,
    pub conf_params: MdtConfParams,
}

/// HsmControlParams used for hsm actions
#[derive(serde::Deserialize, serde::Serialize, Debug, PartialEq, Clone)]
pub struct HsmControlParam {
    pub long_description: String,
    pub param_key: String,
    pub param_value: String,
    pub verb: String,
    pub mdt: Mdt,
}

/// A record and HsmControlParam are triggered when an option is selected.
#[derive(serde::Serialize, Clone, Debug)]
pub struct RecordAndHsmControlParam {
    pub record: Record,
    pub hsm_control_param: HsmControlParam,
}
