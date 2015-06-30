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

var λ = require('highland');
var xmlrpc = require('xmlrpc');
var getSupervisorCredentials = require('./get-supervisor-credentials');

module.exports = function getSupervisorServices () {
  return getSupervisorCredentials()
    .flatMap(function getServicesInfo (creds) {
      var client = xmlrpc.createClient({
        host: 'localhost',
        port: 9100,
        path: '/RPC2',
        basic_auth: creds
      });

      var methodCall = λ.wrapCallback(client.methodCall.bind(client));

      return [methodCall('supervisor.getAllProcessInfo', [])];
    })
    .flatten()
    .filter(function filterRunningServices (service) {
      return service.statename !== 'RUNNING';
    })
    .pluck('name');
};
