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
 * Registers an API
 * @param {Object} requestStore
 * @param {Object} models
 * @param {Object} config
 * @param {Function} registerApiValidator
 * @param {Logger} logger
 * @returns {Function}
 */
exports.wiretree = function registerApiModule(requestStore, models, config, registerApiValidator, logger) {
  /**
   * Validates that the body contains the request, response, and expires properties
   * @param {Object} body
   * @returns {Boolean}
   */
  function validate(body) {
    return registerApiValidator(body).errors.length === 0;
  }

  /**
   * Creates a new request and response object and sends it to the request store.
   * @param {Object} request
   * @param {Object} body
   * @returns {Number}
   */
  return function execute(request, body) {
    var registerResponse = new models.Response(config.status.BAD_REQUEST, config.standardHeaders);

    if (request.method === config.methods.POST && validate(body)) {
      var newRequest = new models.Request(
        body.request.method,
        body.request.url,
        body.request.data,
        body.request.headers
      );

      var newResponse = new models.Response(
        body.response.status,
        body.response.headers,
        body.response.data
      );

      var dependencies = body.dependencies.map(function mapDependencies (dependency) {
        return new models.Request(
          dependency.method,
          dependency.url,
          dependency.data,
          dependency.headers
        );
      });

      logger.trace('registering request');
      requestStore.addEntry(newRequest, newResponse, body.expires, dependencies);

      registerResponse.status = config.status.CREATED;
    }

    return registerResponse;
  };
};
