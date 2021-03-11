// Copyright (c) 2021 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use std::path::PathBuf;

fn main() {
    if !cfg!(target_os = "linux") {
        return;
    }

    println!("cargo:rerun-if-changed=wrapper.h");

    let out_file = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("src")
        .join("bindings.rs");

    if out_file.exists() {
        return;
    }

    let bindings = bindgen::Builder::default()
        .header("wrapper.h")
        .constified_enum_module("boolean")
        .derive_default(true)
        // FID
        .whitelist_type("lu_fid")
        .whitelist_type("lov_user_mds_data_v1")
        .whitelist_type("fid_array")
        .whitelist_var("OBD_MAX_FIDS_IN_ARRAY")
        .whitelist_var("LUSTRE_MAXFSNAME")
        .blacklist_type("lstat_t")
        .generate()
        // Unwrap the Result and panic on failure.
        .expect("Unable to generate bindings");

    bindings
        .write_to_file(out_file)
        .expect("Couldn't write bindings!");
}
