use emf_wire_types::warp_drive::Cache;

pub(crate) fn get_cache() -> Cache {
    static DATA: &'static [u8] = include_bytes!("./fixture.json");

    serde_json::from_slice(&DATA).unwrap()
}
