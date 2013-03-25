//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

(function (_) {
  'use strict';

  /**
   * The purpose of this filter is to convert date strings into a format compatible with angular's expectation of
   * ISO8601 strict.
   */
  angular.module('filters').filter('isoDate', ['$filter', function($filter) {
    var dateFilter = $filter('date');

    return function(date, format) {
      if(_.isString(date)) {
        date = date.replace(/\.\d{6}/g, function (match) {
          return match.substr(0, 4);
        });
      }

      return dateFilter(date, format);
    };
  }]);
}(window.lodash));
