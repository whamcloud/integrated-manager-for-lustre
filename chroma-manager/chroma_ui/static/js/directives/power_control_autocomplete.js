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

  var HOT_KEYS = [8, 40, 38, 13];

  function factory(STATIC_URL) {
    return {
      restrict: 'E',
      templateUrl: '%spartials/directives/power_control_autocomplete.html'.sprintf(STATIC_URL),
      replace: true,
      scope: {
        device: '=',
        host: '=',
        tabIndex: '=',
        onAdd: '&',
        onRemove: '&'
      },
      link: function postLink(scope, element) {
        var input = element.find('input');
        var autoComplete = element.find('.power-states');

        /**
         * A simple wrapper. Makes sure safeApply is always called with the current scope.
         * @param func
         * @returns {function}
         */
        function safeApply(func) {
          return scope.$root.safeApply.bind(null, func, scope);
        }

        /**
         * Sets the dropdown state to active
         * @type {Function}
         */
        var focus = safeApply(function () {
          scope.state = 'active';
          calculatePosition();
        });

        /**
         * Sets the dropdown state to inactive
         * @type {Function}
         */
        var blur = safeApply(function () {
          scope.state = 'inactive';
        });

        function getOutletHostIntersection() {
          var intersection = scope.device.getOutletHostIntersection(scope.host);

          return intersection.filter(scope.outletFilter);
        }

        function getUnassignedOutlets() {
          var unassigned = scope.device.getUnassignedOutlets();

          return unassigned.filter(scope.outletFilter);
        }

        function keydown(event) {
          var key = event.which;

          if (HOT_KEYS.indexOf(key) === -1) {
            return;
          }

          function arrowHandler(defaultIndexValue, returnEarlyFunc, mutatorFunc) {
            var activeIndex = (scope.activeIndex === undefined) ? defaultIndexValue : scope.activeIndex;

            if (returnEarlyFunc(activeIndex)) {
              return;
            }

            scope.setActiveIndex(mutatorFunc(activeIndex));
          }

          var downArrowHandler = arrowHandler.bind(null, -1,
            function returnEarlyFunc(activeIndex) { return activeIndex >= getUnassignedOutlets().length - 1; },
            function mutatorFunc(activeIndex) { return activeIndex + 1; }
          );

          var upArrowHandler = arrowHandler.bind(null, 0,
            function returnEarlyFunc(activeIndex) { return activeIndex === 0; },
            function mutatorFunc(activeIndex) { return activeIndex - 1; }
          );

          function backspaceHandler() {
            var outlets = getOutletHostIntersection();
            var lastOutlet = _.last(outlets);

            if (lastOutlet === undefined) {
              return;
            }

            scope.onRemove({outlet: lastOutlet});
          }

          function enterHandler() {
            var outlet = getUnassignedOutlets()[scope.activeIndex];

            if (outlet === undefined) {
              return;
            }

            scope.onAdd({outlet: outlet, host: scope.host});
            scope.outletFilterText = '';
            upArrowHandler();
          }

          function keydownHandler() {
            if (key === 8 && scope.outletFilterText.length === 0) { // Backspace
              backspaceHandler();
            } else if (key === 40) { // Down Arrow
              downArrowHandler();
            } else if (key === 38) { // Up arrow
              upArrowHandler();
            } else if (key === 13 && scope.activeIndex !== undefined) { // Enter key
              enterHandler();
            }
          }

          safeApply(keydownHandler)();
        }

        /**
         * Focuses the input when clicking the autocomplete.
         * @param {object} event
         */
        function autoCompleteClick(event) {
          if (event.target === input[0] || input.is(':focus')) {
            return;
          }

          input.focus();
        }

        input.on('focus', focus);
        input.on('blur', blur);
        input.on('keydown', keydown);

        autoComplete.on('click', autoCompleteClick);

        function calculatePosition() {
          scope.position = {
            top: autoComplete.outerHeight() + 'px',
            left: 0
          };
        }

        /**
         * The current value of what is typed into the auto complete.
         * @type {string}
         */
        scope.outletFilterText = '';

        /**
         * Sets the active index.
         * @param {number} index
         */
        scope.setActiveIndex = function setActiveIndex(index) {
          scope.activeIndex = index;
        };

        /**
         * Is the index the active one?
         * @param {number} index
         * @returns {boolean}
         */
        scope.isActive = function isActive(index) {
          return index === scope.activeIndex;
        };

        /**
         * Uses outletFilterText to filter the outlet set.
         * @param {PowerControlDeviceOutlet} outlet
         * @returns {boolean} Is there a match?
         */
        scope.outletFilter = function (outlet) {
          var value = scope.outletFilterText.trim();

          if (value === '') {
            return true;
          }

          return outlet.identifier.search(value) !== -1;
        };


        var oldOnAdd = scope.onAdd;
        scope.onAdd = function (locals) {
          oldOnAdd(locals)().then(calculatePosition);
        };

        var oldOnRemove = scope.onRemove;
        scope.onRemove = function (locals) {
          oldOnRemove(locals)().then(calculatePosition);
        };

        scope.$on('$destroy', function destroy() {
          input.off('focus', focus);
          input.off('blur', blur);
          input.off('keydown', keydown);
          autoComplete.off('click', autoCompleteClick);
          oldOnAdd = null;
          oldOnRemove = null;
          input = null;
          autoComplete = null;
          element = null;
        });
      }
    };
  }

  /**
   * Service wrapper for power control auto complete. Useful for testing.
   */
  angular.module('services').factory('powerControlAutocompleteService', ['STATIC_URL', factory]);

  angular.module('directives')
    .directive('powerControlAutocomplete', ['powerControlAutocompleteService', angular.identity]);
}(window.lodash));
