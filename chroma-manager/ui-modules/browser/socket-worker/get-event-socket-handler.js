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

var getEventSocket = require('./get-event-socket');

module.exports = function getEventSocketHandler (socket, workerContext) {

  var eventSockets = {};

  workerContext.addEventListener('message', handler, false);

  function handler (ev) {
    var data = ev.data;
    var type = data.type;

    if (type === 'connect')
      return onConnect(data);
    else if (type === 'send')
      return onSend(data);
    else if (type === 'end')
      return onEnd(data);
  }

  function onConnect (data) {
    if (eventSockets[data.id])
      return;

    eventSockets[data.id] = getEventSocket(socket, data.id, data.options);
  }

  function onSend (data) {
    if (!eventSockets[data.id])
      return;

    var ack;

    if (data.ack)
      ack = fn;
    else
      eventSockets[data.id].onMessage(fn);

    eventSockets[data.id].sendMessage(data.payload, ack);

    function fn (res) {
      workerContext.postMessage({ type: 'message', id: data.id, payload: res });
    }
  }

  function onEnd (data) {
    if (!eventSockets[data.id])
      return;

    eventSockets[data.id].end();
    delete eventSockets[data.id];
  }
};
