//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

angular.module('models').factory('eventModel', ['baseModel', function (baseModel) {
  'use strict';

  return baseModel({
    url: '/api/event/:eventId',
    params: {eventId:'@id'},
    methods: {
      /**
       * @description Returns the state of the event.
       * @returns {string}
       */
      getState: function () {
        return this.severity;
      }
    }
  });
}]);
