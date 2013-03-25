//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

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
