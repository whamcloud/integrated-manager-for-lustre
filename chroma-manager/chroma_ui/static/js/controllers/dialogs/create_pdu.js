//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

(function (_) {
  'use strict';

  function CreatePduCtrl($scope, dialog, PowerControlTypeModel, PowerControlDeviceModel, devices, device) {
    /**
     * @description A generic error callback that can be called for an update or a save.
     * @param {object} resp the error response.
     */
    function errback(resp) {
      if (resp.status === 400) {
        $scope.createPduCtrl.err = angular.isString(resp.data) ? {__all__: [resp.data]} : resp.data;
        $scope.$emit('unblockUi');
      }
    }

    $scope.createPduCtrl = {
      powerControlTypes: PowerControlTypeModel.query(),
      close: dialog.close.bind(dialog),
      closeAlert: function (index) {
        this.err.__all__.splice(index, 1);
      }
    };

    var extension;
    var getDeviceType;

    if (device != null) {
      extension = {
        form: angular.fromJson(angular.toJson(device)), //Remove any possible circular-references.
        submit: function (data) {
          $scope.$emit('blockUi', {fadeIn: true, message: null});
          PowerControlDeviceModel.update(data).$promise.then(function success(resp) {
            angular.copy(resp, device);
            dialog.close();
            $scope.$emit('unblockUi');
          }, errback);
        }
      };

      getDeviceType = function (resp) {
        return _.where(resp, {id: device.device_type.id})[0];
      };
    } else {
      extension = {
        form: {},
        submit: function (data) {
          $scope.$emit('blockUi', {fadeIn: true, message: null});
          PowerControlDeviceModel.save(data).$promise.then(function success() {
            PowerControlDeviceModel.query().$promise.then(function success(resp) {
              angular.copy(resp, devices);
              dialog.close();
              $scope.$emit('unblockUi');
            });
          }, errback);
        }
      };

      getDeviceType = _.first;
    }

    _.extend($scope.createPduCtrl, extension);

    $scope.createPduCtrl.powerControlTypes.$promise.then(function (resp) {
      extension.form.device_type = getDeviceType(resp);
    });
  }

  angular.module('controllers').controller('CreatePduCtrl',
    ['$scope', 'dialog', 'PowerControlTypeModel', 'PowerControlDeviceModel', 'devices', 'device', CreatePduCtrl]
  );
}(window.lodash));
