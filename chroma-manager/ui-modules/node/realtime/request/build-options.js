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

var parse = require('url').parse;
var conf = require('../conf');
var api = parse(conf.get('SERVER_HTTP_URL'));
var stringify = require('querystring').stringify;
var format = require('util').format;
var _ = require('lodash-mixins');
var agent = require('./request-agent').agent;

var defaults = {
  host: api.host,
  hostname: api.hostname,
  port: api.port,
  method: 'GET',
  agent: agent,
  headers: {
    Connection: 'keep-alive',
    'Transfer-Encoding': 'chunked'
  }
};

module.exports = function buildOptions (path, options) {
  path = '/api/' + path
    .replace(/^\/*/, '')
    .replace(/\/*$/, '/');

  var queryString = stringify(options.qs);
  if (queryString)
    path = format('%s?%s', path, queryString);

  var opts =  _.merge({}, defaults, {
    path: path,
    headers: options.headers,
    method: options.method
  });

  if (options.json)
    _.merge(opts, {
      headers: {
        'Content-Type': 'application/json; charset=UTF-8',
        Accept: 'application/json'
      }
    });

  return opts;
};
