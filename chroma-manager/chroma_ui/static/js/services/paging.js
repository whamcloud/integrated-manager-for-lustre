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


(function () {
  'use strict';

  angular.module('services').factory('paging', function () {
    /**
     * @description Parse the offset from the next / previous string.
     * @name getOffset
     * @param {string} direction The property to lookup.
     * @param {object} meta Object used to calculate the offset.
     * @returns {number|undefined}
     */
    function getOffset (direction, meta) {
      if (meta[direction] != null) {
        return parseInt(meta[direction].match(/offset=(\d+)/)[1], 10);
      }
    }

    /**
     * @description Used to parse out pagination properties from the meta object.
     * @class Pager
     * @param {{limit: number, next: string, previous: string, offset: number, total_count: number}} meta
     * @constructor
     */
    function Pager (meta) {
      this.limit = meta.limit;
      this.next = getOffset('next', meta);
      this.previous = getOffset('previous', meta);
      this.noOfPages = (meta.limit === 0? 0: Math.ceil(meta.total_count / meta.limit));
      this.currentPage = (meta.limit === 0? 1: (meta.offset / meta.limit) + 1);
    }

    /**
     * @description Returns params that can be merged in before an api call.
     * @returns {{limit: number, offset: number}}
     */
    Pager.prototype.getParams = function () {
      return {
        limit: this.limit,
        offset: (this.currentPage - 1) * this.limit
      };
    };

    /**
     * @description returns a new Pager
     * @function
     * @param {{limit: number, next: string, previous: string, offset: number, total_count: number}} meta
     */
    return function pagerFactory(meta) {
      return new Pager(meta);
    };
  });
}());
