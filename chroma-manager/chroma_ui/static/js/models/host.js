//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2015 Intel Corporation All Rights Reserved.
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
    params: {hostId: '@id'},
    methods: {
      hasIpmi: function (devices) {
        var ipmi = _.filter(devices, function (device) {
          return device.isIpmi();
        });

        if (ipmi.length === 0) {
          return false;
        }

        var host = this;
        return _.filter(ipmi, function (device) {
          return device.outlets.some(function (outlet) {
            return outlet.host === host.resource_uri;
          });
        }).length > 0;
      },
      hasOutlets: function (devices) {
        var non_ipmi = _.filter(devices, function (device) {
          return !device.isIpmi();
        });

        if (non_ipmi.length === 0) {
          return false;
        }

        var host = this;
        return _.filter(non_ipmi, function (device) {
          return device.outlets.some(function (outlet) {
            return outlet.host === host.resource_uri;
          });
        }).length > 0;
      }
    }
  });

}]);
