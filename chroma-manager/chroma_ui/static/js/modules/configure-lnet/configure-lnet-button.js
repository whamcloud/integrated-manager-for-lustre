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


(function () {
  'use strict';

  angular.module('configureLnet')
    .controller('ConfigureLnetButtonCtrl', ['$scope', '$dialog', 'STATIC_URL', ConfigureLnetButtonCtrl])
    .directive('configureLnetButton', ['STATIC_URL', configureLnetButton]);

  function ConfigureLnetButtonCtrl ($scope, $dialog, STATIC_URL) {
    var dialog = $dialog.dialog({
      keyboard: false,
      backdropClick: false,
      resolve: {
        hostInfo: function getHostInfo () {
          return {
            hostId: $scope.hostId,
            hostName: $scope.hostName
          };
        }
      }
    });

    $scope.configure = function configure() {
      dialog.open(
        STATIC_URL + 'js/modules/configure-lnet/assets/html/configure-lnet.html', 'ConfigureLnetCtrl');
    };
  }

  function configureLnetButton (STATIC_URL) {
    return {
      restrict: 'E',
      scope: {
        hostId: '@',
        hostName: '@'
      },
      templateUrl: STATIC_URL + 'js/modules/configure-lnet/assets/html/configure-lnet-button.html',
      controller: 'ConfigureLnetButtonCtrl'
    };
  }
}());
