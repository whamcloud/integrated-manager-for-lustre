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

/**
 * The request router
 * @param {Object} config
 * @param {Function} dynamicRequest
 * @param {Object} routes
 * @param {Logger} logger
 * @returns {Function}
 */
exports.wiretree = function routerModule(config, dynamicRequest, routes, logger) {
  /**
   * Routes the request appropriately. If the pathname exists in the routes list in the config file then
   * the appropriate handler will be executed. Otherwise, the request will be delegated to the dynamic
   * request processor, which will return a RequestEntry object.
   * @param {String} pathname
   * @param {models.Request} request
   * @param {Object} body
   * @returns {Object | models.RequestEntry}
   */
  return function route(pathname, request, body) {
    // Gate check 1
    if (!pathname) {
      logger.warn('pathname was never passed to the router');

      return {
        status: config.status.NOT_FOUND
      };
    }

    // Gate check 2
    if (request == null) {
      logger.warn('request was never passed to the router');

      return {
        status: config.status.BAD_REQUEST
      };
    }

    // load the appropriate module based on the pathname
    if (routes.restRoutes[pathname]) {
      logger.trace('routing to ' + pathname);
      return routes.restRoutes[pathname](request, body);
    } else {
      // Making a dynamic call to an entry that has been registered.
      logger.trace('making dynamic request');
      return dynamicRequest(request, body);
    }
  };
};
