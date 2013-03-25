//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

angular.module('models').factory('commandModel', ['baseModel', 'STATES', function (baseModel, STATES) {
  'use strict';

  return baseModel({
    url: '/api/command/:commandId',
    params: {commandId:'@id'},
    methods: {
      /**
       * @description Returns the state of the command.
       * @returns {string}
       */
      getState: function () {
        if (!this.complete) {
          return STATES.INCOMPLETE;
        } else if (this.errored) {
          return STATES.ERROR;
        } else if (this.cancelled) {
          return STATES.CANCELED;
        } else {
          return STATES.COMPLETE;
        }
      }
    }
  });
}]);
