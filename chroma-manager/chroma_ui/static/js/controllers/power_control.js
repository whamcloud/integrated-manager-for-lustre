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


(function () {
  'use strict';

  function PowerCtrl($scope, $dialog, $q, hostModel, PowerControlDeviceModel, pageTitle) {
    $scope.$emit('blockUi', {fadeIn: true, message: null});

    pageTitle.set('Configuration - Power Control');

    $scope.powerCtrl = {
      hosts: hostModel.query(),
      powerControlDevices: PowerControlDeviceModel.query({order_by: 'name'}),
      /**
       * Indicates whether or not any of the instantiated devices are IPMI.
       * @returns {Boolean}
       */
      hasIpmi: function (powerControlDevices) {
        return powerControlDevices.some(function (device) {
          return device.isIpmi();
        });
      },
      /**
       * @description Instantiates the and opens add BMC dialog.
       * @param {PowerControlDeviceModel} device
       * @param {hostModel} host
       */
      createBmc: function createBmc(device, host) {
        var dialog = $dialog.dialog({
          resolve: {
            device: function () { return device; },
            host: function () { return host; }
          }
        });

        dialog.open($scope.config.asStatic('partials/dialogs/create_bmc.html'), 'CreateBmcCtrl');
      },
      /**
       * @description Instantiates the and opens create pdu dialog.
       * @param{[PowerControlDeviceModel]} devices
       * @param {PowerControlDeviceModel} [device]
       * @param {boolean} [ipmi]
       */
      createPdu: function createPdu(devices, device, ipmi) {
        var dialog = $dialog.dialog({
          resolve: {
            devices: function () { return devices; },
            device: function () { return device; },
            ipmi: function () { return ipmi; }
          }
        });

        dialog.open($scope.config.asStatic('partials/dialogs/create_pdu.html'), 'CreatePduCtrl');
      },
      /**
       * @description Deletes the given device. Then removes it from the powerControlDevices list.
       * @param {PowerControlDeviceModel} device
       */
      deletePdu: function (device) {
        $scope.$emit('blockUi', {fadeIn: true, message: null});
        device.$delete().then(function success() {
          var deviceIndex = this.powerControlDevices.indexOf(device);
          this.powerControlDevices.splice(deviceIndex, 1);
          $scope.$emit('unblockUi');
        }.bind(this));
      }
    };

    $q.all([$scope.powerCtrl.hosts.$promise, $scope.powerCtrl.powerControlDevices.$promise]).then(function () {
      $scope.$emit('unblockUi');
    });
  }

  angular.module('controllers').controller('PowerCtrl',
    ['$scope', '$dialog', '$q', 'hostModel', 'PowerControlDeviceModel', 'pageTitle', PowerCtrl]
  );
}());


