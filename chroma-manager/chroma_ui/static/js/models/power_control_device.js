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

  function PowerControlDeviceModel(baseModel, PowerControlDeviceOutlet) {
    /**
     * @description Flattens nested device resources before save or update to server.
     * @param {object} data
     * @returns {string}
     */
    function transformRequest(data) {
      var flatData = _.cloneDeep(data);
      //flatten outlets.
      flatData.outlets = _.pluck(data.outlets, 'resource_uri');
      //flatten device_type.
      flatData.device_type = data.device_type.resource_uri;

      return angular.toJson(flatData);
    }

    /**
     * @description sorts a device's outlets then turns each into a PowerControlDeviceOutlet instance.
     * @param {PowerControlDeviceModel} device
     */
    function vivifyOutlets(device) {
      device.outlets.sort(function (a, b) {
        var v1 = a.identifier;
        var v2 = b.identifier;

        if (v1 === v2) {
          return 0;
        }

        return v1 < v2 ? -1 : 1;
      });

      device.outlets = device.outlets.map(function (outlet) {
        return new PowerControlDeviceOutlet(outlet);
      });
    }

    /**
     * @description Represents a power control device and it's outlets.
     * @class PowerControlDeviceModel
     * @returns {PowerControlDeviceModel}
     * @constructor
     */
    return baseModel({
      url: '/api/power_control_device/:powerControlDeviceId',
      params: {powerControlDeviceId: '@id'},
      actions: {
        query: {
          patch: function (devices) {
            devices.forEach(vivifyOutlets);
          }
        },
        save: {
          transformRequest: transformRequest,
          patch: vivifyOutlets
        },
        update: {
          transformRequest: transformRequest,
          patch: vivifyOutlets
        }
      },
      methods: {
        /**
         * Returns a flat list of what outlets are assigned at the intersection of a host and pdu.
         * @param {object} host
         * @returns {Array}
         */
        getOutletHostIntersection: function (host) {
          return this.outlets.filter(function (outlet) {
            return outlet.host === host.resource_uri;
          });
        },
        /**
         * Returns a list of outlets that do not have a host.
         * @returns {Array}
         */
        getUnassignedOutlets: function () {
          return this.outlets.filter(function (outlet) {
            return outlet.host == null;
          });
        },
        /**
         * Removes the outlet from it's host.
         * @param {PowerControlDeviceOutlet} outlet
         * @returns {*}
         */
        removeOutlet: function (outlet) {
          outlet.host = null;
          return outlet.$update();
        },
        removeIpmiOutlet: function (outlet) {
          outlet.host = null;
          return outlet.$delete().then(function () {
            var outletIndex = this.outlets.indexOf(outlet);
            this.outlets.splice(outletIndex, 1);
          }.bind(this));
        },
        /**
         * Adds an outlet to a host.
         * @param {PowerControlDeviceOutlet} outlet
         * @param {hostModel} host
         * @returns {*}
         */
        addOutlet: function (outlet, host) {
          outlet.host = host.resource_uri;
          return outlet.$update();
        },
        format: function (value) {
          return _.pluck(value, 'identifier');
        },
        isIpmi: function () {
          return this.device_type.max_outlets === 0;
        }
      }
    });
  }

  angular.module('models')
    .factory('PowerControlDeviceModel', ['baseModel', 'PowerControlDeviceOutlet', PowerControlDeviceModel]);
}(window.lodash));

