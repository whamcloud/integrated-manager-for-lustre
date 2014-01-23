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

  angular.module('configureLnet')
    .controller('ConfigureLnetButtonCtrl', ['$scope', '$dialog', 'STATIC_URL', ConfigureLnetButtonCtrl])
    .directive('configureLnetButton', ['STATIC_URL', configureLnetButton]);

  function ConfigureLnetButtonCtrl ($scope, $dialog, STATIC_URL) {
    var dialog = $dialog.dialog({
      resolve: {
        hostId: function () { return $scope.hostId; },
        hostName: function () { return $scope.hostName; }
      }
    });

    $scope.disabled = $scope.state !== 'lnet_up';

    $scope.configure = function configure() {
      dialog.open(
        STATIC_URL + 'js/modules/configure-lnet/assets/html/configure-lnet.html', 'ConfigureLnetCtrl');
    };

    var deregister = $scope.$on('toggleLnetConfig', function (event, uri, state) {
      if (uri === $scope.resourceUri)
        $scope.disabled = !state;
    });

    $scope.$on('$destroy', function() {
      deregister();
    });
  }

  function configureLnetButton (STATIC_URL) {
    return {
      restrict: 'E',
      scope: {
        hostId: '@',
        hostName: '@',
        state: '@',
        resourceUri: '@'
      },
      templateUrl: STATIC_URL + 'js/modules/configure-lnet/assets/html/configure-lnet-button.html',
      controller: 'ConfigureLnetButtonCtrl'
    };
  }
}());
