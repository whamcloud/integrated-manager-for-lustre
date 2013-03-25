//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

(function () {
  'use strict';

  /**
   * App module; bootstraps the application.
   */
  angular.module('iml',
      ['controllers', 'models', 'interceptors', 'ngResource', 'constants', 'ui.bootstrap', 'services', 'filters']
    )
    .config(['$interpolateProvider', function ($interpolateProvider) {
      $interpolateProvider.startSymbol('((');
      $interpolateProvider.endSymbol('))');
    }])
    .config(['$httpProvider', function ($httpProvider) {
      $httpProvider.defaults.headers.patch = {'Content-Type': 'application/json;charset=utf-8'};
    }])
    .run(['$rootScope', 'STATIC_URL', function ($rootScope, STATIC_URL) {
      $rootScope.config = {
        asStatic: function (url) {
          return STATIC_URL + url;
        }
      };
    }])
    // TODO: ngInclude -> $anchorScroll -> $location. We do not use $anchorScroll and we do not want to import
    // location as it conflicts with Backbone's router. Remove this when routing goes through Angular.
    .value('$anchorScroll', null);
}());
