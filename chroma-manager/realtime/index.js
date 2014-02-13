//
// INTEL CONFIDENTIAL
//
// Copyright 2013 Intel Corporation All Rights Reserved.
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

function cleanShutdown (signal) {
  console.log('Caught ' + signal + ', shutting down cleanly.');
  // TODO: Is there more that should be done to shut down cleanly?
  process.exit(0);
}

process.on('SIGINT', function () {
  cleanShutdown('SIGINT (Ctrl-C)');
});

process.on('SIGTERM', function () {
  cleanShutdown('SIGTERM');
});

var https = require('https'),
  di = require('di'),
  request = require('request'),
  Q = require('q'),
  serverFactory = require('./server'),
  loggerFactory = require('./logger'),
  conf = require('./conf'),
  primus = require('./primus'),
  Primus = require('primus'),
  streamFactory = require('./stream'),
  multiplex = require('primus-multiplex'),
  resourceFactory = require('./resources').resourceFactory,
  channelFactory = require('./channel'),
  fileSystemResourceFactory = require('./resources').fileSystemResourceFactory,
  hostResourceFactory = require('./resources').hostResourceFactory,
  targetResourceFactory = require('./resources').targetResourceFactory,
  hsmCopytoolResourceFactory = require('./resources').hsmCopytoolResourceFactory,
  hsmCopytoolOperationResourceFactory = require('./resources').hsmCopytoolOperationResourceFactory,
  targetOstMetricsResourceFactory = require('./resources').targetOstMetricsResourceFactory,
  timers = require('./timers');

var modules = [{
  conf: ['value', conf],
  https: ['value', https],
  logger: ['factory', loggerFactory],
  Primus: ['value', Primus],
  multiplex: ['value', multiplex],
  request: ['value', request],
  Q: ['value', Q],
  timers: ['value', timers],
  channelFactory: ['factory', channelFactory],
  Stream: ['factory', streamFactory],
  FileSystemResource: ['factory', fileSystemResourceFactory],
  HostResource: ['factory', hostResourceFactory],
  primus: ['factory', primus],
  Resource: ['factory', resourceFactory],
  server: ['factory', serverFactory],
  TargetResource: ['factory', targetResourceFactory],
  HsmCopytoolResource: ['factory', hsmCopytoolResourceFactory],
  HsmCopytoolOperationResource: ['factory', hsmCopytoolOperationResourceFactory],
  TargetOstMetricsResource: ['factory', targetOstMetricsResourceFactory]
}];

var injector = new di.Injector(modules);

injector.invoke(function (logger, channelFactory,
                          FileSystemResource, HostResource, TargetResource,
                          HsmCopytoolResource, HsmCopytoolOperationResource,
                          TargetOstMetricsResource) {

  logger.info('Realtime Module started.');

  channelFactory('filesystem', FileSystemResource);
  channelFactory('host', HostResource);
  channelFactory('target', TargetResource);
  channelFactory('copytool', HsmCopytoolResource);
  channelFactory('copytool_operation', HsmCopytoolOperationResource);
  channelFactory('targetostmetrics', TargetOstMetricsResource);
});
