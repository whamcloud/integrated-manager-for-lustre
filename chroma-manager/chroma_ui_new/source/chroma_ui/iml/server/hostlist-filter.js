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


angular.module('server').factory('hostlistFilter', ['pdshFilter', 'naturalSortFilter',
  /**
   * The filter used to filter the rows on the server table. It receives the list of original
   * server objects, which was sent by the server spark. These server objects are first passed into
   * the pdsh filter. The result of this filter is then passed into the natural sort filter.
   * @param {Function} pdshFilter
   * @param {Function} naturalSortFilter
   * @returns {Object}
   */
    function hostlistFilterFactory (pdshFilter, naturalSortFilter) {
      'use strict';

      var getter = _.property('address');
      var state = {
        hosts: null,
        hash: null,
        fuzzy: null,
        reverse: null
      };

      var hostlistFilter = {
        compute: function compute () {
          var pdshFilterResults = pdshFilter(state.hosts, state.hash, getter, state.fuzzy);
          return naturalSortFilter(pdshFilterResults, getter, state.reverse);
        }
      };

      Object.keys(state).reduce(function (hostlistFilter, key) {
        hostlistFilter['set' + _.capitalize(key)] = function setter (newVal) {
          state[key] = newVal;

          return this;
        };

        return hostlistFilter;
      }, hostlistFilter);

      return hostlistFilter;
    }]);
