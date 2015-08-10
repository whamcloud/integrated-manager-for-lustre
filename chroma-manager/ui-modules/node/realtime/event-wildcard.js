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


var emit = require('events').EventEmitter.prototype.emit;
var _ = require('lodash-mixins');

module.exports = function eventWildcard (socket, next) {
  if (socket.onevent !== onEvent)
    socket.onevent = onEvent;

  return next();
};

function onEvent (packet) {
  /*jshint validthis:true */
  var args = packet.data || [];

  if (packet.id != null)
    args.push(this.ack(packet.id));

  emit.apply(this, args);

  var wildcardArgs = _.cloneDeep(args);
  var eventName = wildcardArgs.splice(0, 1, '*');

  wildcardArgs[1] = wildcardArgs[1] || {};
  wildcardArgs[1].eventName = eventName[0];

  emit.apply(this, wildcardArgs);
}
