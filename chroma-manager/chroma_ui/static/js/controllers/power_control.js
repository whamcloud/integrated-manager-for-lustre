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

  function PowerCtrl($scope, $dialog, $q, hostModel, PowerControlDeviceModel) {
    $scope.$emit('blockUi', {fadeIn: true, message: null});

    $scope.powerCtrl = {
      hosts: hostModel.query(),
      powerControlDevices: PowerControlDeviceModel.query({order_by: 'name'}),
      /**
       * Returns the classes available on a given outlet.
       * @param {PowerControlDeviceOutlet} outlet
       * @returns {Array}
       */
      getOptionClass: function (outlet) {
        var classes = [outlet.hasPower()];

        if (!outlet.isAvailable()) {
          classes.push('select2-selected');
        }

        return classes;
      },
      /**
       * @description Instantiates the and opens create pdu dialog.
       * @param{[PowerControlDeviceModel]} devices
       * @param {PowerControlDeviceModel} [device]
       */
      createPdu: function createPdu(devices, device) {
        var dialog = $dialog.dialog({
          resolve: {
            devices: function () { return devices; },
            device: function () { return device; }
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
      },
      /**
       * @description Formats the tag css class with the outlets current state.
       * @param {object} obj
       * @returns {string}
       */
      formatTagCssClass: function formatTagCssClass(obj) {
        var outlet = getScope(obj.element).outlet;
        return outlet.hasPower();
      },
      /**
       * @description Formats the outlet select item text.
       * @param {object} obj
       * @returns {string}
       */
      formatResult: function formatResult(obj) {
        var outlet = getScope(obj.element).outlet;
        return 'Outlet: %s'.sprintf(outlet.identifier);
      }
    };

    function getScope(el) {
      return angular.element(el).scope();
    }

    $q.all([$scope.powerCtrl.hosts, $scope.powerCtrl.powerControlDevices]).then(function () {
      $scope.$emit('unblockUi');
    });
  }

  angular.module('controllers').controller('PowerCtrl',
    ['$scope', '$dialog', '$q', 'hostModel', 'PowerControlDeviceModel', PowerCtrl]
  );
}());


