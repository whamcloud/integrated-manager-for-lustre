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

process.on('SIGINT', cleanShutdown('SIGINT (Ctrl-C)'));
process.on('SIGTERM', cleanShutdown('SIGTERM'));

function cleanShutdown (signal) {
  return function cleanShutdownInner () {
    console.log('Caught ' + signal + ', shutting down cleanly.');
    // Exit with 0 to keep supervisor happy.
    process.exit(0);
  };
}

var WireTree = require('wiretree');
var getRouter = require('router');
var _ = require('lodash-mixins');
var requestStream = require('request-stream');
var http = require('http');
var conf = require('./conf');

http.globalAgent.maxSockets = 200;

if (require.main === module)
  createWireTree().resolve();
else
  module.exports = createWireTree;

/**
 * Creates a new WireTree instance and returns it.
 * @returns {Object}
 */
function createWireTree () {
  var tree = new WireTree(__dirname);

  tree.add('process', process)
    .add('fs', require('fs'))
    .add('path', require('path'))
    .add('getRouter', getRouter)
    .add('_', _)
    .add('requestStream', function requestWithApiUrl (path, options) {
      path = path
        .replace(/^\/*/, '')
        .replace(/\/*$/, '/');

      return requestStream(conf.apiUrl + path, options);
    })
    .add('errorSerializer', require('bunyan').stdSerializers.err)
    .add('http', http)
    .add('format', require('util').format)
    .add('conf', conf);

  var deps = {
    'through': 'through',
    highland: 'λ',
    bunyan: 'bunyan',
    './logger': 'logger',
    crypto: 'crypto',
    xmlrpc: 'xmlrpc',
    child_process: 'childProcess',
    './view-server': 'viewServer',
    './view-router': 'viewRouter'
  };

  Object.keys(deps).forEach(function addDep (dep) {
    tree.add(deps[dep], require(dep));
  });

  var folders = [
    '/view-server',
    '/middleware',
    '/routes',
    '/lib'
  ];

  folders.forEach(function loadFolder (path) {
    tree.folder(__dirname + path, { transform: transform });
  });

  return tree;
}

/**
 * Capitalizes parts of a string.
 * @param {String} text
 * @returns {String}
 */
function transform (text) {
  return text.split(/\-|\./).reduce(function convert (str, part) {
    return str += _.capitalize(part);
  });
}
