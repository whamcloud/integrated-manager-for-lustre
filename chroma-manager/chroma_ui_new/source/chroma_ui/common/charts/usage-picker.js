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

angular.module('charts')
.directive('usagePicker', [function usagePicker () {
  'use strict';

  return {
    restrict: 'E',
    replace: true,
    templateUrl: 'common/charts/assets/html/usage-picker.html',
    scope: {
      onUpdate: '&'
    },
    controller: ['$scope', function controller ($scope) {
      $scope.usage = {
        percentage: 0,
        /**
         * Sets up an on submit handler for the form
         * and recalculates the popover layout when the transcluded scope changes.
         * @param {object} actions An object of actions that can be performed on the popover
         */
        work: function work (actions) {
          this.onSubmit = function onSubmit () {
            $scope.onUpdate({percentage: this.percentage});

            this.currentPercentage = this.percentage;

            actions.hide();
          };
        }
      };

      $scope.usage.currentPercentage = $scope.usage.percentage;
    }]
  };
}]);

