//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

angular.module('models').factory('hostModel', ['baseModel', function (baseModel) {
  'use strict';

  /**
   * @description Represents a host
   * @class hostModel
   * @returns {hostModel}
   * @constructor
   */
  return baseModel({
    url: '/api/host/:hostId',
    params: {hostId: '@id'}
  });

}]);
