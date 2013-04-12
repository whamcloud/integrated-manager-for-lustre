//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

(function (_) {
  'use strict';

  /**
   * Upper case the first character of the passed in string.
   */
  angular.module('filters').filter('capitalize', [function () {
    return function (word) {
      if (_.isString(word)) {
        word = word.charAt(0).toUpperCase() + word.slice(1);
      }

      return word;
    };
  }]);
}(window.lodash));
