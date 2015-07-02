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

module.exports = function getEventConnection (socket, id) {
  var lastSend;

  var eventSocket = Object.create(socket);

  eventSocket.end = function end () {
    if (!socket) return;

    socket.emit('end' + id);
    onDestroy();
    socket = eventSocket = null;
  };

  eventSocket.sendMessage = function sendMessage (data, ack) {
    if (typeof ack !== 'function')
      lastSend = arguments;

    socket.emit('message' + id, data, ack);
    return this;
  };

  eventSocket.onMessage = function onMessage (fn) {
    socket.on('message' + id, fn);
    return this;
  };

  socket.on('reconnect', onReconnect);

  function onReconnect () {
    if (lastSend && eventSocket)
      eventSocket.sendMessage.apply(eventSocket, lastSend);
  }

  socket.once('destroy', onDestroy);
  function onDestroy () {
    if (!socket) return;

    socket.removeAllListeners('message' + id);
    socket.off('reconnect', onReconnect);
  }

  return eventSocket;
};
