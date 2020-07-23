// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, env};
use iml_wire_types::LdevEntry;
use tokio::{
    fs::File,
    io::AsyncWriteExt,
};

async fn write_to_file(content: String) -> Result<(), ImlAgentError> {
    let ldev_path = env::get_var("LDEV_CONF_PATH");

    let mut file = File::create(ldev_path).await?;
    file.write_all(content.as_bytes()).await?;

    Ok(())
}

async fn create_ldev_conf_internal<F>(entries: Vec<LdevEntry>, write_to_file: impl Fn(String) -> F) -> Result<(), ImlAgentError> 
where F: futures::Future<Output=Result<(), ImlAgentError>>
{
    let content = entries
        .iter()
        .map(|x| x.to_string())
        .collect::<Vec<String>>()
        .join("\n");
    
    write_to_file(content).await?;

    Ok(())
}

pub async fn create_ldev_conf(entries: Vec<LdevEntry>) -> Result<(), ImlAgentError> {
    create_ldev_conf_internal(entries, write_to_file).await?;
    
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_create_ldev_conf() -> Result<(), ImlAgentError> {
        // oss2 oss1 zfsmo-OST0013 zfs:ost19/ost19
        let entries = vec![
            LdevEntry {
                primary: "mds1".into(),
                failover: Some("mds2".into()),
                label: "MGS".into(),
                device: "zfs:mdt0/mdt0".into(),
            },
            LdevEntry {
                primary: "mds1".into(),
                failover: Some("mds2".into()),
                label: "zfsmo-MDT0000".into(),
                device: "zfs:mdt0/mdt0".into(),
            },
            LdevEntry {
                primary: "mds2".into(),
                failover: Some("mds1".into()),
                label: "zfsmo-MDT0001".into(),
                device: "zfs:mdt1/mdt1".into(),
            },
            LdevEntry {
                primary: "oss1".into(),
                failover: Some("oss2".into()),
                label: "zfsmo-OST0000".into(),
                device: "zfs:ost0/ost0".into(),
            },
            LdevEntry {
                primary: "oss1".into(),
                failover: Some("oss2".into()),
                label: "zfsmo-OST0001".into(),
                device: "zfs:ost1/ost1".into(),
            },
            LdevEntry {
                primary: "oss1".into(),
                failover: Some("oss2".into()),
                label: "zfsmo-OST0002".into(),
                device: "zfs:ost2/ost2".into(),
            },
            LdevEntry {
                primary: "oss1".into(),
                failover: Some("oss2".into()),
                label: "zfsmo-OST0003".into(),
                device: "zfs:ost3/ost3".into(),
            },
            LdevEntry {
                primary: "oss1".into(),
                failover: Some("oss2".into()),
                label: "zfsmo-OST0004".into(),
                device: "zfs:ost4/ost4".into(),
            },
            LdevEntry {
                primary: "oss1".into(),
                failover: Some("oss2".into()),
                label: "zfsmo-OST0005".into(),
                device: "zfs:ost5/ost5".into(),
            },
            LdevEntry {
                primary: "oss1".into(),
                failover: Some("oss2".into()),
                label: "zfsmo-OST0006".into(),
                device: "zfs:ost6/ost6".into(),
            },
            LdevEntry {
                primary: "oss1".into(),
                failover: Some("oss2".into()),
                label: "zfsmo-OST0007".into(),
                device: "zfs:ost7/ost7".into(),
            },
            LdevEntry {
                primary: "oss1".into(),
                failover: Some("oss2".into()),
                label: "zfsmo-OST0008".into(),
                device: "zfs:ost8/ost8".into(),
            },
            LdevEntry {
                primary: "oss1".into(),
                failover: Some("oss2".into()),
                label: "zfsmo-OST0009".into(),
                device: "zfs:ost9/ost9".into(),
            },
            LdevEntry {
                primary: "oss2".into(),
                failover: Some("oss1".into()),
                label: "zfsmo-OST000a".into(),
                device: "zfs:ost10/ost10".into(),
            },
            LdevEntry {
                primary: "oss2".into(),
                failover: Some("oss1".into()),
                label: "zfsmo-OST000b".into(),
                device: "zfs:ost11/ost11".into(),
            },
            LdevEntry {
                primary: "oss2".into(),
                failover: Some("oss1".into()),
                label: "zfsmo-OST000c".into(),
                device: "zfs:ost12/ost12".into(),
            },
            LdevEntry {
                primary: "oss2".into(),
                failover: Some("oss1".into()),
                label: "zfsmo-OST000d".into(),
                device: "zfs:ost13/ost13".into(),
            },
            LdevEntry {
                primary: "oss2".into(),
                failover: Some("oss1".into()),
                label: "zfsmo-OST000e".into(),
                device: "zfs:ost14/ost14".into(),
            },
            LdevEntry {
                primary: "oss2".into(),
                failover: Some("oss1".into()),
                label: "zfsmo-OST000f".into(),
                device: "zfs:ost15/ost15".into(),
            },
            LdevEntry {
                primary: "oss2".into(),
                failover: Some("oss1".into()),
                label: "zfsmo-OST00010".into(),
                device: "zfs:ost16/ost16".into(),
            },
            LdevEntry {
                primary: "oss2".into(),
                failover: Some("oss1".into()),
                label: "zfsmo-OST00011".into(),
                device: "zfs:ost17/ost17".into(),
            },
            LdevEntry {
                primary: "oss2".into(),
                failover: Some("oss1".into()),
                label: "zfsmo-OST00012".into(),
                device: "zfs:ost18/ost18".into(),
            },
            LdevEntry {
                primary: "oss2".into(),
                failover: Some("oss1".into()),
                label: "zfsmo-OST00013".into(),
                device: "zfs:ost19/ost19".into(),
            },
        ];

        async fn write_to_file(content: String) -> Result<(), ImlAgentError> {
            insta::assert_snapshot!(content);

            Ok(())
        }

        create_ldev_conf_internal(entries, write_to_file).await?;

        Ok(())
    }
}
