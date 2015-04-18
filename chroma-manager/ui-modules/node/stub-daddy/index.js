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

var Wiretree = require('wiretree');
var url = require('url');
var http = require('http');
var https = require('https');
var path = require('path');
var Validator = require('jsonschema').Validator;
var bunyan = require('bunyan');
var querystring = require('querystring');
var configulator = require('configulator');
var fs = require('fs');
var Promise = require('promise');
var format = require('util').format;
var _ = require('lodash-mixins');

/**
 * Creates the wiretree
 * @param {String} [protocol]
 * @returns {Object}
 */
module.exports = function createWireTree (protocol) {
  var wireTree = new Wiretree(__dirname);

  wireTree.add(url, 'url');
  wireTree.add(path, 'path');
  wireTree.add(Validator, 'Validator');
  wireTree.add(bunyan, 'bunyan');
  wireTree.add(querystring, 'querystring');
  wireTree.add(configulator, 'configulator');
  wireTree.add(Promise, 'Promise');
  wireTree.add(fs, 'fs');
  wireTree.add(format, 'format');
  wireTree.add(_, '_');
  wireTree.load('./webservice.js', 'webService');
  wireTree.load('./inline-service.js', 'inlineService');
  wireTree.load('./router.js', 'router');
  wireTree.load('./request-store.js', 'requestStore');
  wireTree.load('./validators/request-validator.js', 'requestValidator');
  wireTree.load('./matcher.js', 'requestMatcher');
  wireTree.load('./mock-state.js', 'mockState');
  wireTree.load('./mock-list.js', 'mockList');
  wireTree.load('./dynamic-request.js', 'dynamicRequest');
  wireTree.load('./mock-status.js', 'mockStatus');
  wireTree.load('./register-api.js', 'registerApi');
  wireTree.load('./flush-state.js', 'flushState');
  wireTree.load('./validators/register-api-validator.js', 'registerApiValidator');
  wireTree.load('./models.js', 'models');
  wireTree.load('./config.js', 'config');
  wireTree.load('./routes.js', 'routes');
  wireTree.load('./logger.js', 'logger');
  wireTree.load('./fsReadThen.js', 'fsReadThen');

  var config = wireTree.get('config');

  if (protocol)
    config.requestProtocol = protocol;

  var request = (config.requestProtocol === 'https') ? https : http;

  wireTree.add(request, 'request');

  return {
    config: wireTree.get('config'),
    webService: wireTree.get('webService'),
    inlineService: wireTree.get('inlineService'),
    validator: wireTree.get('registerApiValidator')
  };
};

