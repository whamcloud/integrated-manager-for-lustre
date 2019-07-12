// Copyright (c) 2019 DDN. All rights reserved.
// Use of this source code is governed by a MIT-style
// license that can be found in the LICENSE file.

use seed::document;

/// Will return https://<domain>:<port>/ui/
pub fn ui_root() -> String {
  document().base_uri().unwrap().unwrap_or_default()
}

/// Will return https://<domain>:<port>/grafana/
pub fn grafana_root() -> String {
  let url = document().base_uri().unwrap().unwrap_or_default();
  url.replace("/ui/", "/grafana/")
}