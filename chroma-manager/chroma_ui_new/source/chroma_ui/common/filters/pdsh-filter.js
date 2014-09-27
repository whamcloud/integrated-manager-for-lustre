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

angular.module('filters').filter('pdsh', [function pdsh () {
  'use strict';

  /**
   * Given an array of objects, return a list of objects that match the list of host names.
   * @param {Array} [input]
   * @param {Object} [hostnamesHash]
   * @param {Function} hostPath Function used to retrieve the hostName property from the object passed in
   * @param {Boolean} [fuzzy] Indicates if the filtering should be done on a fuzzy match.
   * @returns {Array}
   */
  return function pdshExpander (input, hostnamesHash, hostPath, fuzzy) {
    input = input || [];
    hostnamesHash = hostnamesHash || {};
    var hostnames = Object.keys(hostnamesHash);

    var filteredItems = input.filter(filterInputByHostName(hostnamesHash, hostnames, hostPath, fuzzy));

    return (hostnames.length > 0) ? filteredItems : input;
  };

  /**
   * Filters the input by the host name
   * @param {Object} hostnamesHash
   * @param {Array} hostnames
   * @param {Function} hostPath
   * @param {Boolean} fuzzy
   * @returns {Function}
   */
  function filterInputByHostName (hostnamesHash, hostnames, hostPath, fuzzy) {

    /**
     * Filters the input by the host name
     * @param {String} item
     * @returns {Boolean}
     */
    return function innerFilterInputByHostName (item) {
      if (fuzzy) {
        var matches = hostnames.filter(filterCurrentItemByHostNameList(hostPath(item), fuzzy));
        return matches.length > 0;
      } else {
        return hostnamesHash[hostPath(item)] != null;
      }
    };
  }

  /**
   * Filters on the current item by the host name list
   * @param {String} item
   * @param {Boolean} fuzzy
   * @returns {Function}
   */
  function filterCurrentItemByHostNameList(item, fuzzy) {

    /**
     * Filters on the current item by the host name list
     * @param {String} hostname
     * @returns {Boolean}
     */
    return function innerFilterCurrentItemByHostNameList (hostname) {
      return (fuzzy === true) ? item.indexOf(hostname) > -1 : item === hostname;
    };
  }
}]);


