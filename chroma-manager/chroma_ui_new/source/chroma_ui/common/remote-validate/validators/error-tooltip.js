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

  angular.module('validators', ['tooltipPosition'])
    .service('errorTooltipService',
      ['$compile', '$timeout', '$parse', '$window', '$document', '$animate', 'tooltipPosition',
        function ($compile, $timeout, $parse, $window, $document, $animate, tooltipPosition) {
          return {
            restrict: 'A',
            scope: true,
            link: function link(scope, element, attrs) {
              var template = '<error-tooltip-popup ' +
                'errors="errors" ' +
                'placement = "tooltipPlacement" ' +
                '>' +
              '</error-tooltip-popup>';

              var tooltip = $compile(template)(scope);

              /**
               * Puts the tooltip into the correct position and shows it.
               * @returns {void}
               */
              function show() {
                // Don't show empty tooltip.
                if (_.isEmpty(scope.errors)) return;

                // Let the event loop turn
                // To put tooltip in the right position.
                $timeout(function () {
                  if (!$document[0].body.contains(tooltip[0])) {
                    // Set the initial positioning.
                    _.extend(tooltip[0].style, {top: 0, left: 0, display: 'block'});

                    element.after(tooltip);
                  }

                  setPosition();

                  $animate.addClass(tooltip, 'in', function () {
                    angular.element($window).on('resize', throttledResize);
                  });
                });
              }

              function setPosition() {
                // clone the node.
                var clone = tooltip[0].cloneNode(true),
                  wrappedClone = angular.element(clone),
                  directions = _.values(tooltipPosition.DIRECTIONS),
                  directionsJoined = _.values(tooltipPosition.DIRECTIONS).join(' '),
                  windowPosition = tooltipPosition.positioner($window),
                  clonePosition = tooltipPosition.positioner(clone);

                // place the clone.
                element.after(clone);

                directions.splice(directions.indexOf(preferredPlacement), 1);
                directions.unshift(preferredPlacement);

                // check where clone fits.
                directions.some(function (direction) {
                  wrappedClone
                  .removeClass('in ' + directionsJoined)
                  .addClass(direction);

                  var position = tooltipPosition.position(direction, clonePosition);

                  _.extend(clone.style, position);

                  var fits = !tooltipPosition.overflows(direction, windowPosition, clonePosition);

                  if (fits) {
                    console.log(direction);
                    scope.tooltipPlacement = direction;
                    _.extend(tooltip[0].style, position);
                  }

                  return fits;
                });

                //destroy the clone
                angular.element(clone).remove();
                clone = null;
              }

              var throttledResize = _.throttle(function() {
                if (!tooltip.hasClass('in')) return;

                setPosition();
                scope.$digest();
              }, 500);

              /**
               * Hides the tooltip by removing it from the DOM.
               */
              function hide() {
                $animate.removeClass(tooltip, 'in', function () {
                  tooltip.remove();

                  angular.element($window).off('resize', throttledResize);
                });
              }

              /**
               * When the errors change hide or show the tooltip accordingly.
               */
              attrs.$observe('errorTooltip', function (val) {
                scope.errors = $parse(val)(scope);

                if (_.isEmpty(scope.errors))
                  hide();
                else
                  show();
              });

              var preferredPlacement, secondaryPlacement;

              /**
               * If the placement changes update the scope.
               */
              attrs.$observe('errorTooltipPlacement', function (val) {
                if (Array.isArray(val)) {
                  scope.tooltipPlacement = val.shift();
                  secondaryPlacement = val.shift();
                } else {
                  scope.tooltipPlacement = val || tooltipPosition.DIRECTIONS.TOP;
                  secondaryPlacement = undefined;
                }

                if (!preferredPlacement) preferredPlacement = scope.tooltipPlacement;
              });

              element
                .bind('focus', function () {
                  scope.$apply(show);
                })
                .bind('blur', function () {
                  scope.$apply(hide);
                });

              scope.$on('$destroy', function onDestroy() {
                element
                  .unbind('focus')
                  .unbind('blur');

                hide();

                element = null;
                tooltip = null;
              });
            }
          };
        }
      ]
    )
    .directive('errorTooltipPopup', ['STATIC_URL', function (STATIC_URL) {
      return {
        restrict: 'EA',
        replace: true,
        scope: { title: '@', errors: '=', placement: '=', animation: '&', isOpen: '&' },
        templateUrl: '%scommon/remote-validate/validators/assets/error-tooltip.html'.sprintf(STATIC_URL)
      };
    }])
  /**
   * A tooltip for displaying server-side errors on a form.
   * @name errorTooltip
   * @example
   * <input error-tooltip="((serverValidationError.username))" error-tooltip-placement="right" />
   * @see {@link http://angular-ui.github.io/bootstrap/#/tooltip|Tooltip Options}
   */
    .directive('errorTooltip', ['errorTooltipService', angular.identity]);
}());
