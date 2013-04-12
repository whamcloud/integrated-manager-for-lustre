//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

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


