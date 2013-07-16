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


(function (_) {
  'use strict';

  angular.module('validators', ['responsive'])
    .constant('TOOLTIP_POSITIONS', {
      TOP: 'top',
      RIGHT: 'right',
      BOTTOM: 'bottom',
      LEFT: 'left'
    })
    .service('errorTooltipService',
      ['$compile', '$timeout', '$parse', '$window', '$document', '$position',
        'TOOLTIP_POSITIONS', 'responsive_comparator', 'responsive_SIZES',
        function ($compile, $timeout, $parse, $window, $document, $position, TOOLTIP_POSITIONS, comparator, SIZES) {
          return {
            restrict: 'A',
            scope: true,
            link: function link(scope, element, attrs) {
              var originalTooltipPlacement;
              var template = '<error-tooltip-popup ' +
                'errors="((errors))" ' +
                'placement = "((tooltipPlacement))" ' +
                'is-open="tooltipIsOpen"' +
                '>' +
                '</error-tooltip-popup>';

              var tooltip = $compile(template)(scope);

              /**
               * Move the tooltip as the window resizes.
               * Throttled to 20 ms.
               * @type {Function}
               */
              var throttledResize = _.throttle(function () {
                show();
                scope.$digest();
              }, 20);

              var positions = {};

              positions[TOOLTIP_POSITIONS.RIGHT] = {
                top: function (position, tooltipDimensions) {
                  return position.top + position.height / 2 - tooltipDimensions.height / 2;
                },
                left: function (position) {
                  return position.left + position.width;
                }
              };

              positions[TOOLTIP_POSITIONS.BOTTOM] = {
                top: function (position) {
                  return position.top + position.height;
                },
                left: function (position, tooltipDimensions) {
                  return position.left + position.width / 2 - tooltipDimensions.width / 2;
                }
              };

              positions[TOOLTIP_POSITIONS.LEFT] = {
                top: positions[TOOLTIP_POSITIONS.RIGHT].top,
                left: function (position, tooltipDimensions) {
                  return position.left - tooltipDimensions.width;
                }
              };

              positions[TOOLTIP_POSITIONS.TOP] = {
                top: function (position, tooltipDimensions) {
                  return position.top - tooltipDimensions.height;
                },
                left: positions[TOOLTIP_POSITIONS.BOTTOM].left
              };

              /**
               * Finds The correct position to place the tooltip
               * @returns {Object}
               */
              function getPosition() {
                if (!$document[0].body.contains(tooltip[0])) {
                  // Set the initial positioning.
                  tooltip.css({ top: 0, left: 0, display: 'block' });

                  element.after(tooltip);
                }

                // Get the position of the directive element.
                var position = $position.position(element);

                // Get the height and width of the tooltip so we can center it.
                var tooltipDimensions = {
                  height: tooltip.prop('offsetHeight'),
                  width: tooltip.prop('offsetWidth')
                };

                // Calculate the tooltip's top and left coordinates to center it with
                // this directive.
                return _.assign({}, positions[scope.tooltipPlacement], function mutator(objVal, srcVal) {
                  return srcVal(position, tooltipDimensions) + 'px';
                });
              }

              /**
               * Puts the tooltip into the correct position and shows it.
               * @returns {void}
               */
              function show() {
                // Don't show empty tooltip.
                if (_.isEmpty(scope.errors)) {
                  return;
                }

                var result = comparator(SIZES.TABLET);

                scope.tooltipPlacement = (result >= 0 ? scope.tooltipSecondaryPlacement : originalTooltipPlacement);

                // Let the event loop turn
                // To put tooltip arrow in the right position.
                $timeout(function () {
                  tooltip.css(getPosition());
                });

                scope.tooltipIsOpen = true;

                angular.element($window).bind('resize', throttledResize);
              }

              /**
               * Hides the tooltip by removing it from the DOM.
               * @returns {void}
               */
              function hide() {
                scope.tooltipIsOpen = false;

                tooltip.remove();

                // Angular's JQLite throws if the event isn't bound.
                try {
                  angular.element($window).unbind('resize', throttledResize);
                } catch (error) {
                  var expected = error instanceof TypeError;

                  if (!expected) {
                    throw error;
                  }
                }
              }

              /**
               * When the errors change hide or show the tooltip accordingly.
               */
              attrs.$observe('errorTooltip', function (val) {
                scope.errors = $parse(val)(scope);

                if (_.isEmpty(scope.errors)) {
                  hide();
                } else {
                  $timeout(show);
                }
              });

              /**
               * If the placement changes update the scope.
               */
              attrs.$observe('errorTooltipPlacement', function (val) {
                scope.tooltipPlacement = originalTooltipPlacement = val || TOOLTIP_POSITIONS.TOP;
              });

              /**
               * If the secondary placement changes update the scope.
               */
              attrs.$observe('errorTooltipSecondaryPlacement', function (val) {
                scope.tooltipSecondaryPlacement = val || TOOLTIP_POSITIONS.BOTTOM;
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
        templateUrl: '%spartials/directives/error-tooltip.html'.sprintf(STATIC_URL)
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
}(window.lodash));

