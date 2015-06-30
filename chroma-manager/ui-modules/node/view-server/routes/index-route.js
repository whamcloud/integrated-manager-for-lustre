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

var viewRouter = require('../view-router');
var indexHandlers = require('../lib/index-handlers');
var checkGroup = require('../lib/check-group');

module.exports = function indexRoute () {
  viewRouter.get('/ui/configure/hsm', indexHandlers.newHandler);
  viewRouter.get('/ui/configure/server/:id*', indexHandlers.newHandler);

  viewRouter.route('/ui/configure/:subpath+')
    .get(checkGroup.fsAdmins)
    .get(indexHandlers.oldHandler);

  viewRouter.route('/ui/target/:id')
    .get(checkGroup.fsAdmins)
    .get(indexHandlers.oldHandler);

  viewRouter.route('/ui/job/:id')
    .get(checkGroup.fsAdmins)
    .get(indexHandlers.oldHandler);

  viewRouter.route('/ui/storage_resource/:id')
    .get(checkGroup.fsAdmins)
    .get(indexHandlers.oldHandler);

  viewRouter.route('/ui/user/:id')
    .get(checkGroup.fsUsers)
    .get(indexHandlers.oldHandler);

  viewRouter.route('/ui/system_status')
    .get(checkGroup.fsAdmins)
    .get(indexHandlers.oldHandler);

  viewRouter.get('/ui/command/:id', indexHandlers.oldHandler);
  viewRouter.get('/ui/alert', indexHandlers.oldHandler);
  viewRouter.get('/ui/event', indexHandlers.oldHandler);
  viewRouter.get('/ui/log/:around*', indexHandlers.oldHandler);
  viewRouter.get('/ui/status', indexHandlers.oldHandler);
  viewRouter.get('/(.*)', indexHandlers.newHandler);
};
