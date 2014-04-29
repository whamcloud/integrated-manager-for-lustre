//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2014 Intel Corporation All Rights Reserved.
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

  function CreatePduCtrl($scope, dialog, PowerControlTypeModel, PowerControlDeviceModel, devices, device, ipmi) {
    /**
     * @description A generic error callback that can be called for an update or a save.
     * @param {object} resp the error response.
     */
    function errback(resp) {
      if (resp.status === 400)
        $scope.createPduCtrl.err = angular.isString(resp.data) ? {__all__: [resp.data]} : resp.data;

      $scope.$emit('unblockUi');
    }

    $scope.createPduCtrl = {
      close: dialog.close.bind(dialog),
      closeAlert: function (index) {
        this.err.__all__.splice(index, 1);
      }
    };

    var extension;
    var getDeviceType;

    if (device != null) {
      extension = {
        form: angular.copy(device),
        submit: function (data) {
          $scope.$emit('blockUi', {fadeIn: true, message: null});
          data.$update().then(function success(resp) {
            angular.copy(resp, device);
            dialog.close();
            $scope.$emit('unblockUi');
          }, errback);
        },
        type: 'edit',
        ipmi: ipmi,
        title: 'Edit Pdu: %s'.sprintf(device.name)
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
        },
        type: 'add',
        ipmi: ipmi,
        title: ipmi ? 'Configure IPMI' : 'New PDU'
      };

      if (ipmi != null) {
        // Special case for IPMI support -- force-select the IPMI type.
        getDeviceType = function (resp) {
          return _.find(resp, function (type) {
            return type.max_outlets === 0;
          });
        };
      } else {
        getDeviceType = _.first;
      }
    }

    _.extend($scope.createPduCtrl, extension);

    PowerControlTypeModel.query().$promise.then(function (resp) {
      if (ipmi != null) {
        $scope.createPduCtrl.powerControlTypes = resp;
        extension.form.name = 'IPMI';
        extension.form.address = '0.0.0.0';
      } else {
        // Filter out IPMI types for non-IPMI PDU creation
        $scope.createPduCtrl.powerControlTypes = resp.filter(function (type) {
          return type.max_outlets > 0;
        });
      }

      extension.form.device_type = getDeviceType(resp);
    });
  }

  angular.module('controllers').controller('CreatePduCtrl',
    ['$scope', 'dialog', 'PowerControlTypeModel', 'PowerControlDeviceModel', 'devices', 'device', 'ipmi', CreatePduCtrl]
  );
}(window.lodash));
