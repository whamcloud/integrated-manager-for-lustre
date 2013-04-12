//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

(function () {
  'use strict';

  /**
   * @description Represents a power control device item
   * @class PowerControlTypeModel
   * @param {object} baseModel
   * @returns {PowerControlTypeModel}
   * @constructor
   */
  function PowerControlTypeModel(baseModel) {
    return baseModel({
      url: '/api/power_control_type'
    });
  }

  angular.module('models').factory('PowerControlTypeModel', ['baseModel', PowerControlTypeModel]);
}());
