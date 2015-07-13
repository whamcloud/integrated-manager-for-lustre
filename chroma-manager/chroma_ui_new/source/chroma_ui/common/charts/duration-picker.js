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

  var DURATIONS = {
    MINUTES: 'minutes',
    HOURS: 'hours',
    DAYS: 'days',
    WEEKS: 'weeks'
  };

  var singularRegexp = /s{1}$/;

  Object.freeze(DURATIONS);

  angular.module('charts')
  .constant('DURATIONS', DURATIONS)
  .directive('durationPicker', ['DURATIONS', durationPicker]);

  function durationPicker (DURATIONS) {
    return {
      restrict: 'E',
      replace: true,
      templateUrl: 'common/charts/assets/html/duration-picker.html',
      scope: {
        onUpdate: '&',
        startUnit: '@',
        startSize: '@'
      },
      controller: ['$scope', function controller ($scope) {
        $scope.duration = {
          unit: $scope.startUnit || DURATIONS.MINUTES,
          size: parseInt($scope.startSize, 10) || 1,
          units: [
            {unit: DURATIONS.MINUTES, count: 60},
            {unit: DURATIONS.HOURS, count: 24},
            {unit: DURATIONS.DAYS, count: 31},
            {unit: DURATIONS.WEEKS, count: 4}
          ],
          /**
           * Gets the associated count for a unit.
           * @param {string} unit
           * @returns {number|undefined} The count or undefined if a match was not found.
           */
          getCount: function getCount (unit) {
            var item = this.units.filter(function (item) {
              return item.unit === unit;
            }).pop();

            if (item) return item.count;
          },
          /**
           * Sets the unit to the passed in value. Also resets size to 1;
           * @param {string} unit
           */
          setUnit: function setUnit (unit) {
            this.unit = unit;
            this.size = 1;
          },
          /**
           * Sets up an on submit handler for the form
           * and recalculates the popover layout when the transcluded scope changes.
           * @param {object} actions An object of actions that can be performed on the popover
           */
          work: function work (actions) {
            this.onSubmit = function onSubmit () {
              $scope.onUpdate({unit: this.unit, size: this.size});

              this.currentUnit = this.unit;
              this.currentSize = this.size;

              actions.hide();
            };
          },
          /**
           * Takes a plural duration and converts it to a singular representation.
           * @param {string} duration
           * @returns {string} The singular duration.
           */
          singular: function singular (duration) {
            return duration.replace(singularRegexp, '');
          }
        };

        $scope.duration.currentUnit = $scope.duration.unit;
        $scope.duration.currentSize = $scope.duration.size;
      }]
    };
  }
}());

