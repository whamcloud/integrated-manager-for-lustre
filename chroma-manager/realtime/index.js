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

process.on('SIGINT', cleanShutdown('SIGINT (Ctrl-C)'));
process.on('SIGTERM', cleanShutdown('SIGTERM'));

function cleanShutdown (signal) {
  return function cleanShutdownInner () {
    console.log('Caught ' + signal + ', shutting down cleanly.');
    // TODO: Is there more that should be done to shut down cleanly?
    process.exit(0);
  };
}

var di = require('di');
var fs = require('fs');
var router = require('socket-router');
var resources = require('./resources');
var path = require('path');
var Validator = require('jsonschema').Validator;

var http = require('http');

http.globalAgent.maxSockets = 25;

var modules = [{
  conf: ['value', require('./conf')],
  http: ['value', http],
  _: ['value', require('lodash-mixins')],
  Primus: ['value', require('primus')],
  jsonMask: ['value', require('json-mask')],
  serverWrite: ['value', require('./primus-server-write')],
  multiplex: ['value', require('primus-multiplex')],
  Emitter: ['value', require('primus-emitter')],
  VERBS: ['value', router.verbs],
  errorSerializer: ['value', require('bunyan').stdSerializers.err],
  MultiplexSpark: ['value', require('primus-multiplex/lib/server/spark')],
  logger: ['factory', require('./logger')],
  loop: ['factory', require('./loop-factory')],
  primusServerWrite: ['factory', require('./primus-server-write')],
  requestChannel: ['factory', require('./request-channel')],
  requestModule: ['value', require('request')],
  request: ['factory', require('./request')],
  Q: ['value', require('q')],
  timers: ['value', require('./timers')],
  router: ['value', router],
  channelFactory: ['factory', require('./channel')],
  Stream: ['factory', require('./stream')],
  FileSystemResource: ['factory', resources.fileSystemResourceFactory],
  HostResource: ['factory', resources.hostResourceFactory],
  primus: ['factory', require('./primus')],
  Resource: ['factory', resources.resourceFactory],
  TargetResource: ['factory', resources.targetResourceFactory],
  HsmCopytoolResource: ['factory', resources.hsmCopytoolResourceFactory],
  HsmCopytoolOperationResource: ['factory', resources.hsmCopytoolOperationResourceFactory],
  TargetOstMetricsResource: ['factory', resources.targetOstMetricsResourceFactory],
  AlertResource: ['factory', resources.alertResourceFactory],
  EventResource: ['factory', resources.eventResourceFactory],
  CommandResource: ['factory', resources.commandResourceFactory],
  NotificationResource: ['factory', resources.notificationResourceFactory],
  requestChannelValidator: ['factory', require('./req-channel-validator')],
  validator: ['value', new Validator()],
  promisedFile: ['value', require('promised-file')],
  srcmapReverse: ['value', require('srcmap-reverse')]
}];

loadDir('./routes');

var injector = new di.Injector(modules);

injector.invoke(function (logger, channelFactory,
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
});

function loadDir (dir) {
  var files = fs.readdirSync(path.normalize(__dirname + '/' + dir));

  files.forEach(function (file) {
    var withoutExtension = file.split('.').slice(0, -1).join('.');
    var withoutExtensionParts = withoutExtension.split('-');
    var type = withoutExtensionParts.pop().toLowerCase();
    var name = withoutExtensionParts.join('-');

    modules[0][camelCaseText(name)] = [type, require(dir + '/' + withoutExtension)];
  });
}

function camelCaseText (text) {
  return text.split('-').reduce(function convert (str, part) {
    return (str += part.charAt(0).toUpperCase() + part.slice(1));
  });
}
