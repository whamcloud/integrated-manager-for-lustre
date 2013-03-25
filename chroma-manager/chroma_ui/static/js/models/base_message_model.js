//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

(function (_) {
  'use strict';

  angular.module('models').factory('baseMessageModel', ['$resource', function ($resource) {
    return function getModel(config) {
      var defaults = {
        params: {},
        actions: {
          loadAll: {
            method: 'GET',
            isArray: true,
            params: {
              limit: 0
            }
          }
        }
      };

      _.merge(defaults, config);

      if (defaults.url === undefined) {
        throw new Error('A url property must be provided to BaseMessageModel');
      }

      return $resource(defaults.url, defaults.params, defaults.actions);
    };
  }]);
}(window.lodash));
