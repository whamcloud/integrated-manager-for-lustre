//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

/**
 * A Factory for accessing alerts.
 */
angular.module('models').factory('alertModel', ['baseModel', 'STATES', function (baseModel, STATES) {
  'use strict';

  return baseModel({
    url: '/api/alert/:alertId',
    params: {alertId:'@id'},
    methods: {
      /**
       * @description Returns the state of the alert (which is always STATES.ERROR).
       * @returns {string}
       */
      getState: function () {
        return STATES.ERROR;
      }
    }
  });
}]);

