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

var nconf = require('nconf');
var url = require('url');
var _ = require('lodash-mixins');
var path = require('path');
var fs = require('fs');

var managerDir = _.range(3).reduce(function getLogPath (dir) {
  return path.dirname(dir);
}, __dirname);

var managerPath = path.join.bind(path.join, managerDir);

// Indicate that the memory store will be used so values can be set after nconf is defined.
nconf.use('memory');
var conf = nconf
  .env()
  .argv()
  .file(__dirname + '/conf.json')
  .defaults({
    LOG_PATH: '',
    LOG_FILE: 'view_server.log'
  });

// Set the appropriate values when in the test environment
if (conf.get('NODE_ENV') === 'test') {
  conf.set('SERVER_HTTP_URL', 'https://localhost:8000/');
  conf.set('IS_RELEASE', false);
  conf.set('ALLOW_ANONYMOUS_READ', true);
  conf.set('STATIC_URL', '/static/');
  conf.set('VERSION', '');
  conf.set('BUILD', 'jenkins__');
  conf.set('VIEW_SERVER_PORT', 8889);
  conf.set('LOG_PATH', managerDir);

  var helpText = fs.readFileSync(managerPath('chroma_help', 'help.py'), { encoding: 'utf8' })
    .match(/({[\s\S]*})/mg)[0]
    .replace(/"""/mg, '\'')
    .replace(/: "(.+)"/mg, ': \'($1)\'')
    .replace(/\\'/mg, '\'')
    .replace(/"/mg, '\\"')
    .replace(/'(.+)':/gm, '"$1":')
    .replace(/: '(.+)',/gm, ': "$1",')
    .replace(/: '\n([\s\S]+)',/mg, ': "$1"')
    .replace(/\n/mg, '');

  conf.set('HELP_TEXT', JSON.parse(helpText));
}

var parsedApiHttpUrl = url.parse(conf.get('SERVER_HTTP_URL'));
parsedApiHttpUrl.pathname = '/api/';
conf.overrides({
  API_PORT: parsedApiHttpUrl.port,
  API_URL: url.format(parsedApiHttpUrl),
  HOST_NAME: parsedApiHttpUrl.hostname,
  PARSED_API_URL: parsedApiHttpUrl,
  SITE_ROOT: managerPath(),
  TEMPLATE_ROOT: managerPath('chroma_ui', 'templates') + path.sep
});

module.exports = _.mapKeys(conf.load(), _.flip(_.camelCase));
