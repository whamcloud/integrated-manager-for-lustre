// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use mount_emitter::{get_write_stream, looper, stdin_to_file, write_all};

fn main() {
    tokio::run(looper(stdin_to_file, get_write_stream, write_all))
}
