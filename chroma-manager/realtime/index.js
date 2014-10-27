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
    // TODO: Is there more that should be done to shut down cleanly?
    process.exit(0);
  };
}

var WireTree = require('wiretree');
var router = require('socket-router');
var Validator = require('jsonschema').Validator;
var _ = require('lodash-mixins');
var http = require('http');
http.globalAgent.maxSockets = 25;

if (require.main === module) {
  var tree = createWireTree();
  tree.get('main');
} else {
  module.exports = createWireTree;
}

/**
 * Creates a new WireTree instance and returns it.
 * @param {Object} [conf] A conf to use.
 * @returns {Object}
 */
function createWireTree (conf) {
  var tree = new WireTree(__dirname);

  tree.add(router, 'router');
  tree.add(router.verbs, 'VERBS');
  tree.add(new Validator(), 'validator');
  tree.add(_, '_');
  tree.add(require('bunyan').stdSerializers.err, 'errorSerializer');

  conf = conf || require('./conf');
  tree.add(conf, 'conf');

  var deps = {
    './channel': 'channelFactory',
    'json-mask': 'jsonMask',
    './logger': 'logger',
    './loop-factory': 'loop',
    primus: 'Primus',
    './primus': 'primus',
    'primus-emitter': 'Emitter',
    'primus-multiplex': 'multiplex',
    './primus-server-write': 'primusServerWrite',
    'promised-file': 'promisedFile',
    q: 'Q',
    request: 'requestModule',
    './request-factory': 'request',
    './request-channel': 'requestChannel',
    './req-channel-validator': 'requestChannelValidator',
    'srcmap-reverse': 'srcmapReverse',
    './stream': 'Stream',
    'primus-multiplex/lib/server/spark': 'MultiplexSpark',
    './timers': 'timers'
  };

  tree.folder(__dirname + '/routes', {
    transform: transform
  });

  tree.folder(__dirname + '/resources', {
    transform: transformUpper
  });

  Object.keys(deps).forEach(function addDep (dep) {
    tree.add(require(dep), deps[dep]);
  });

  tree.add({ wiretree: main }, 'main');

  return tree;
}

function main (logger, channelFactory,
                          FileSystemResource, HostResource, TargetResource, TargetOstMetricsResource,
                          HsmCopytoolResource, HsmCopytoolOperationResource,
                          NotificationResource, requestChannel) {

  logger.info('Realtime Module started.');

  requestChannel();

  channelFactory('filesystem', FileSystemResource);
  channelFactory('host', HostResource);
  channelFactory('target', TargetResource);
  channelFactory('copytool', HsmCopytoolResource);
  channelFactory('copytool_operation', HsmCopytoolOperationResource);
  channelFactory('targetostmetrics', TargetOstMetricsResource);
  channelFactory('notification', NotificationResource);
}

function transform (text) {
  return text.split(/\-|\./).reduce(function convert (str, part) {
    return str += _.capitalize(part);
  });
}

function transformUpper (text) {
  return transform(_.capitalize(text));
}
