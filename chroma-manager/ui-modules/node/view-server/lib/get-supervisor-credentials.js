//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2014 Intel Corporation All Rights Reserved.
//
// The source code contained or described herein and all documents related
// to the source code ("Material") are owned by Intel Corporation or its
// suppliers or licensors. Title to the Material remains with Intel Corporation
// or its suppliers and licensors. The Material contains trade secrets and
// proprietary and confidential information of Intel or its suppliers and
// licensors. The Material is protected by worldwide copyright and trade secret
// laws and treaty provisions. No part of the Material may be used, copied,
// reproduced, modified, published, uploaded, posted, transmitted, distributed,
// or disclosed in any way without Intel's prior express written permission.
//
// No license under any patent, copyright, trade secret or other intellectual
// property right is granted to or conferred upon you by disclosure or delivery
// of the Materials, either expressly, by implication, inducement, estoppel or
// otherwise. Any license under such intellectual property rights must be
// express and approved by Intel in writing.

'use strict';

var λ = require('highland');
var _ = require('lodash-mixins');
var childProcess = require('child_process');
var conf = require('../conf');
var crypto = require('crypto');

var credentials;
var command = 'python -c "import settings; print settings.SECRET_KEY"';

var exec = λ.wrapCallback(childProcess.exec);

module.exports = function getSupervisorCredentials () {
  if (conf.nodeEnv === 'production')
    credentials = [null, null];

  var credentialsStream;

  if (credentials) {
    credentialsStream = λ(credentials);
  } else {
    var userStream = exec(command, { cwd: conf.siteRoot })
      .invoke('trim', [])
      .through(getHash())
      .invoke('slice', [0, 7]);

    var passwordStream = userStream
      .observe()
      .through(getHash());

    credentialsStream = λ([userStream, passwordStream])
      .sequence();
  }

  return credentialsStream
    .collect()
    .tap(function (c) {
      credentials = c;
    })
    .stopOnError(console.log)
    .map(_.partial(_.zipObject, ['user', 'pass']));

  function getHash () {
    var hash = crypto.createHash('md5');
    hash.setEncoding('hex');

    return hash;
  }
};
