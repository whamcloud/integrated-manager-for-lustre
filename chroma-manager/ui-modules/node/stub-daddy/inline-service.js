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

exports.wiretree = function getInlineService (config, registerApiValidator, logger, router, requestValidator,
                                              requestStore, mockStatus, format, _) {

  var pp = _.partialRight(JSON.stringify, null, 2);

  function handleError (item, type, errors) {
    var message = format('The %s is invalid: \n\n %s \n\n Reasons: \n\n %s',
      type,
      pp(item),
      pp(errors)
    );
    throw new Error(message);
  }

  return {
    /**
     * Add a new mock
     * @param {Object} mock
     * @returns {Object}
     */
    mock: function addMock (mock) {
      var errors = registerApiValidator(mock).errors;

      if (errors.length > 0) {
        handleError(mock, 'mock', errors);
      }

      return handleRequest({
        url: config.requestUrls.MOCK_REQUEST,
        method: config.methods.POST,
        data: mock,
        headers: {}
      });
    },
    /**
     * Retrieve the mock state.
     * @returns {Object} A promise.
     */
    mockState: function mockState () {
      return this.makeRequest({
        url: config.requestUrls.MOCK_STATE,
        method: config.methods.GET,
        headers: {}
      });
    },
    /** Retrieve the mock state.
     * @returns {Object} A promise.
     */
    registeredMocks: function listRegisteredMocks () {
      return this.makeRequest({
        url: config.requestUrls.MOCK_LIST,
        method: config.methods.GET,
        headers: {}
      });
    },
    /**
     * Make a generic request
     * @param {Object} options
     * @returns {Object} A promise
     */
    makeRequest: function makeRequest (options) {
      var errors = requestValidator(options).errors;

      if (errors.length > 0) {
        handleError(options, 'request', errors);
      }

      return handleRequest(options);
    },

    /**
     * Flushes the entries in the request store and the requests in the mock state module.
     */
    flush: function flushEntries() {
      requestStore.flushEntries();
      mockStatus.flushRequests();
    }
  };

  /**
   * Handles an incoming request.
   * @param {Object} options
   */
  function handleRequest(options) {
    logger.trace({
      pathname: options.url,
      body: options.data
    }, 'Request received');

    // Delegate the request to the router, where it will be processed and return a response.
    return handleResponse(router(options.url, options, options.data));
  }

  /**
   * Handles processing the response returned by the router
   * @param {Object} evaluatedResponse
   */
  function handleResponse(evaluatedResponse) {

    var props = ['status', 'data'];
    var debugData = _.pick(evaluatedResponse, props);

    if (!Object.keys(debugData)) {
      var vals = _.fill(new Array(props.length), config.status.NOT_FOUND);
      debugData = _.zipObject(props, vals);
    }

    var debugMessage = (evaluatedResponse ? 'Response received.' : 'Request not found, no status');

    logger.trace(debugData, debugMessage);

    var responseProps = ['data', 'headers', 'status'];
    var returnObj = _.pick(evaluatedResponse, responseProps);

    if (!Object.keys(returnObj))
      returnObj = _.zipObject(responseProps, [null, {}, config.status.NOT_FOUND]);

    return returnObj;
  }
};
