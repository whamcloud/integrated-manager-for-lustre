// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

extern crate bindgen;

use std::env;

fn main() {
    let out_file = env::current_dir().unwrap().join("src").join("bindings.rs");

    // Tell cargo to tell rustc to link the system bzip2
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
        // // Logging
        // .constified_enum_module("llapi_message_level")
        // .whitelist_function("llog_error")
        // .whitelist_function("llog_printf")
        // FID
        .whitelist_type("lustre_fid")
        //.whitelist_function("llapi_fd2fid")
        .whitelist_function("llapi_path2fid")
        .whitelist_function("llapi_fid2path")
        // .whitelist_function("llapi_fd2parent")
        // .whitelist_function("llapi_path2parent")
        // // File
        // .whitelist_type("llapi_stripe_param")
        // .whitelist_function("llapi_file_open_param")
        // .whitelist_function("llapi_file_create")
        // .whitelist_function("llapi_file_create_pool")
        // .whitelist_function("llapi_file_open")
        // .whitelist_function("llapi_file_open_pool")
        // .whitelist_function("llapi_file_get_stripe")
        // .whitelist_function("llapi_file_lookup")
        // .whitelist_function("llapi_file_fget_mdtidx")
        // .whitelist_function("llapi_poollist")
        // .whitelist_function("llapi_get_poollist")
        // .whitelist_function("llapi_get_poolmembers")
        // // Stat
        .whitelist_type("obd_statfs")
        .whitelist_function("llapi_obd_statfs")
        // // Find
        // .whitelist_type("find_param")
        // .whitelist_function("llapi_find")
        // .whitelist_function("llapi_ostlist")
        // .whitelist_function("llapi_getstripe")
        // .whitelist_function("llapi_uuid_match")
        // Dir
        // Finish the builder and generate the bindings.
        .generate()
        // Unwrap the Result and panic on failure.
        .expect("Unable to generate bindings");

    bindings
        .write_to_file(out_file)
        .expect("Couldn't write bindings!");
}
