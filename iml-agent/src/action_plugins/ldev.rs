// Copyright (c) 2020 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use crate::{agent_error::ImlAgentError, env};
use iml_wire_types::LdevEntry;
use std::collections::BTreeSet;
use tokio::{
    fs::{File, OpenOptions},
    io::{AsyncReadExt, AsyncWriteExt},
};

async fn write_to_file(content: String) -> Result<(), ImlAgentError> {
    let ldev_path = env::get_ldev_conf();
    let mut file = File::create(ldev_path).await?;
    file.write_all(content.as_bytes()).await?;

    Ok(())
}

async fn read_ldev_config() -> Result<String, ImlAgentError> {
    let ldev_path = env::get_ldev_conf();

    let mut file = OpenOptions::new()
        .read(true)
        .write(true)
        .create(true)
        .open(ldev_path)
        .await?;

    let mut buffer = String::new();
    file.read_to_string(&mut buffer).await?;

    Ok(buffer)
}

fn parse_entries(ldev_config: String) -> BTreeSet<LdevEntry> {
    ldev_config.lines().map(LdevEntry::from).collect()
}

fn config_needs_update_check(
    existing_entries: &BTreeSet<LdevEntry>,
    entries: &BTreeSet<LdevEntry>,
) -> bool {
    let diff: Vec<_> = existing_entries
        .symmetric_difference(&entries)
        .cloned()
        .collect();

    !diff.is_empty()
}

fn convert(entries: &[LdevEntry]) -> String {
    entries
        .iter()
        .map(|x| x.to_string())
        .collect::<Vec<String>>()
        .join("\n")
}

pub async fn create(entries: Vec<LdevEntry>) -> Result<(), ImlAgentError> {
    let ldev_config = read_ldev_config().await?;
    let existing_entries = parse_entries(ldev_config);
    let entries_set = entries.iter().cloned().collect::<BTreeSet<LdevEntry>>();
    if config_needs_update_check(&existing_entries, &entries_set) {
        let data = convert(&entries);
        write_to_file(data).await?;
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_create() -> Result<(), ImlAgentError> {
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
                label: "zfsmo-OST0010".into(),
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
        ]
        .into_iter()
        .collect::<Vec<LdevEntry>>();

        let data = convert(&entries);
        insta::assert_snapshot!(data);

        Ok(())
    }

    #[test]
    fn test_config_without_ha() -> Result<(), ImlAgentError> {
        let entries = vec![
            LdevEntry {
                primary: "mds1".into(),
                failover: None,
                label: "MGS".into(),
                device: "zfs:mdt0/mdt0".into(),
            },
            LdevEntry {
                primary: "mds1".into(),
                failover: Some("mds2".into()),
                label: "zfsmo-MDT0000".into(),
                device: "zfs:mdt0/mdt0".into(),
            },
        ]
        .into_iter()
        .collect::<Vec<LdevEntry>>();

        let data = convert(&entries);
        insta::assert_snapshot!(data);

        Ok(())
    }

    #[test]
    fn test_config_needs_update() -> Result<(), ImlAgentError> {
        let existing_entries: String = r#"mds1 mds2 MGS zfs:mdt0/mdt0
mds1 mds2 zfsmo-MDT0000 zfs:mdt0/mdt0"#
            .into();
        let existing_entries = parse_entries(existing_entries)?;

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
                primary: "oss1".into(),
                failover: Some("oss2".into()),
                label: "zfsmo-OST0005".into(),
                device: "zfs:ost5/ost5".into(),
            },
        ]
        .into_iter()
        .collect::<BTreeSet<LdevEntry>>();

        assert_eq!(config_needs_update_check(&existing_entries, &entries), true);

        Ok(())
    }

    #[test]
    fn test_config_does_not_need_updating() -> Result<(), ImlAgentError> {
        let existing_entries = vec![
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
        ]
        .into_iter()
        .collect::<BTreeSet<LdevEntry>>();

        let entries: String = r#"mds1 mds2 MGS zfs:mdt0/mdt0
mds1 mds2 zfsmo-MDT0000 zfs:mdt0/mdt0"#
            .into();
        let entries = parse_entries(entries)?;

        assert_eq!(
            config_needs_update_check(&existing_entries, &entries),
            false
        );

        Ok(())
    }
}
