// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

fn main() {
    let out_file = std::env::current_dir()
        .unwrap()
        .join("src")
        .join("bindings.rs");

    // Tell cargo to tell rustc to link the system liblustreapi
    // shared library.
    println!("cargo:rustc-link-lib=lustreapi");

    if out_file.exists() {
        return;
    }

    // The bindgen::Builder is the main entry point
    // to bindgen, and lets you build up options for
    // the resulting bindings.
    let bindings = bindgen::Builder::default()
        .header("wrapper.h")
        .constified_enum_module("boolean")
        .derive_default(true)
        // FID
        .whitelist_type("lustre_fid")
        .whitelist_function("llapi_path2fid")
        .whitelist_function("llapi_fid2path")
        // Stat
        .blacklist_type("lstat_t")
        .whitelist_type("lov_user_mds_data")
        .whitelist_type("lov_user_mds_data_v1")
        .whitelist_function("llapi_search_rootpath")
        .generate()
        // Unwrap the Result and panic on failure.
        .expect("Unable to generate bindings");

    bindings
        .write_to_file(out_file)
        .expect("Couldn't write bindings!");
}
