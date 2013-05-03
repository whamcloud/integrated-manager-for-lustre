//
// INTEL CONFIDENTIAL
//
// Copyright 2013 Intel Corporation All Rights Reserved.
//
// The source code contained or described herein and all documents related
// to the source code ("Material") are owned by Intel Corporation or its
// suppliers or licensors. Title to the Material remains with Intel Corporation
// or its suppliers and licensors. The Material contains trade secrets and
// proprietary and confidential information of Intel or its suppliers and
// licensors. The Material is protected by worldwide copyright and trade secret
// laws and treaty provisions. No part of the Material may be used, copied,
// reproduced, modified, published, uploaded, posted, transmitted, distributed,
// or disclosed in any way without Intel's prior express written permission.
//
// No license under any patent, copyright, trade secret or other intellectual
// property right is granted to or conferred upon you by disclosure or delivery
// of the Materials, either expressly, by implication, inducement, estoppel or
// otherwise. Any license under such intellectual property rights must be
// express and approved by Intel in writing.


(function (_) {
  'use strict';

  angular.module('models').factory('PowerControlDeviceOutlet', ['baseModel', function (baseModel) {
    /**
     * @description Represents a power control device outlet
     * @class PowerControlDeviceOutlet
     * @returns {PowerControlDeviceOutlet}
     * @constructor
     */
    return baseModel({
      url: '/api/power_control_device_outlet/:powerControlDeviceOutletId',
      params: {powerControlDeviceOutletId: '@id'},
      methods: {
        /**
         * Does this outlet have a host?
         * @returns {boolean}
         */
        isAvailable: function () {
          return this.host === null;
        },
        /**
         * A more friendly string based version of has_power.
         * @returns {string}
         */
        hasPower: function () {
          var states = {
            on: true,
            off: false,
            unknown: null
          };

          return _.findKey(states, function (val) {
            return val === this.has_power;
          }.bind(this));
        }
      }
    });
  }]);

}(window.lodash));
