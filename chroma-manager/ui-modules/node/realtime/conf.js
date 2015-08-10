//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2015 Intel Corporation All Rights Reserved.
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

var nconf = require('nconf');
var path = require('path');
var _ = require('lodash-mixins');

var conf = nconf
  .env()
  .argv()
  .file(__dirname + '/conf.json')
  .defaults({
    LOG_FILE: 'realtime.log',
    NODE_ENV: 'development'
  });

if (conf.get('NODE_ENV') === 'test') {
  var logDir = _.range(3).reduce(function getLogPath (dir) {
    return path.dirname(dir);
  }, __dirname);

  conf.set('SERVER_HTTP_URL', 'https://localhost:8000/');
  conf.set('SOURCE_MAP_PATH', __dirname + '/test/integration/fixtures/built-fd5ce21b.js.map');
  conf.set('REALTIME_PORT', 8888);
  conf.set('LOG_PATH', logDir);
}

module.exports = conf;
