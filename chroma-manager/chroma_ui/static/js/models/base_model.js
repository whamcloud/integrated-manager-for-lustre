//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

(function (_) {
  'use strict';

  angular.module('models').factory('baseModel', ['$resource', 'paging', function ($resource, paging) {
    /**
     * @description Represents the base model.
     * @class baseModel
     * @returns {baseModel}
     * @constructor
     */
    return function getModel(config) {
      var defaults = {
        params: {},
        actions: {
          get: {method: 'GET'},
          save: {method: 'POST'},
          update: {method: 'PUT'},
          remove: {method: 'DELETE'},
          delete: {method: 'DELETE'},
          patch: {method: 'PATCH'},
          query: {
            method: 'GET',
            isArray: true,
            patch: function (value, resp) {
              value.paging = paging(resp.props.meta);
            }
          }
        },
        methods: {}
      };

      _.merge(defaults, config);

      if (defaults.url === undefined) {
        throw new Error('A url property must be provided to baseModel');
      }

      return $resource(defaults.url, defaults.params, defaults.actions, defaults.methods);
    };
  }]);
}(window.lodash));
