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
 * Returns a function that indicates whether two request objects match.
 * @param {url.Url} url
 * @returns {Function}
 */
exports.wiretree = function matcherModule(url) {
  /**
   * Higher order function that generates a function to be used in comparison.
   * @param {Object} object1
   * @param {Object} object2
   * @param {String} propertyName
   * @returns {Function}
   */
  function createComparisonFunction(object1, object2, propertyName) {
    return function comparisonFunction(element) {
      var object1Property = JSON.stringify(object1[propertyName][element]);
      var object2Property = JSON.stringify(object2[propertyName][element]);

      return object1Property === object2Property;
    };
  }

  /**
   * Attempts to match the incoming request with a registered request. The important thing to note here
   * is that while the registeredRequest may have x, y, and z properties in data or headers and the incoming
   * request may have more, we are only concerned with whether or not the properties in the registered request
   * all exist and match in the incoming request. The fact that the incomingRequest may have more properties on
   * data or header doesn't affect the outcome.
   * @param {models.Request} incomingRequest
   * @param {models.Request} registeredRequest
   * @returns {Boolean}
   */
   return function match(incomingRequest, registeredRequest) {
    var isMatch = (incomingRequest.method === registeredRequest.method) &&
      (url.parse(incomingRequest.url).pathname === url.parse(registeredRequest.url).pathname);

    /**
     * Compares the requests based on a specified property.
     * @param {String} property
     * @returns {Boolean}
     */
    function compare(property) {
      var comparator = createComparisonFunction(registeredRequest, incomingRequest, property);
      return Object.keys(registeredRequest[property]).every(comparator);
    }

    // For data, we only care to verify that the data in the registered request exists
    // in the incoming request. It's perfectly fine if the incoming request contains more
    // data than what's in the registered request, so long as it contains all of the data
    // that is in the registered request.
    return isMatch && compare('data') && compare('headers');
  };
};
