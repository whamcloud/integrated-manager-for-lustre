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

var http = require('http');
var https = require('https');
var loginRoute = require('./routes/login-route');
var indexRoute = require('./routes/index-route');
var viewRouter = require('./view-router');
var conf = require('./conf');

// Don't limit to pool to 5 in node 0.10.x
https.globalAgent.maxSockets = http.globalAgent.maxSockets = Infinity;

loginRoute();
indexRoute();

module.exports = function start () {
  return http.createServer(function createServer (req, res) {
    viewRouter.go(req.url,
      {
        verb: req.method,
        clientReq: req
      },
      {
        clientRes: res,
        redirect: function redirect (path) {
          res.writeHead(302, { Location: path });
          res.end();
        }
      }
    );
  }).listen(conf.viewServerPort);
};
