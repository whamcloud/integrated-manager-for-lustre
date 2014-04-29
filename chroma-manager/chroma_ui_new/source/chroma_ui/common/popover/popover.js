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


angular.module('iml-popover', ['position']).directive('imlPopover', ['position', '$timeout', '$window',
  function (position, $timeout, $window) {
    'use strict';

    return {
      restrict: 'E',
      transclude: true,
      replace: true,
      scope: {
        placement: '@',
        title: '@',
        work: '&'
      },
      templateUrl: 'common/popover/assets/html/popover.html',
      controller: ['$transclude', function($transclude) {
        this.$transclude = $transclude;
      }],
      link: function (scope, el, attrs, controller) {
        var popoverButton = el.siblings('.activate-popover').eq(0),
          wrappedWindow = angular.element($window);

        if (!popoverButton) throw new Error('No popover button found!');

        var positioner = position.positioner(el[0]);

        scope.open = false;

        controller.$transclude(function(clone, transcludedScope) {
          el.find('.popover-content').append(clone);

          if (scope.work) {
            scope.work({
              transcludedScope: transcludedScope,
              actions: {
                recalculate: function () {
                  $timeout(recalculate);
                },
                hide: hide
              }
            });
          }
        });

        popoverButton.on('click', function ($event) {
          scope.$apply(function () { toggle($event); });
        });

        el.on('click', function ($event) { $event.stopPropagation(); });

        scope.$on('$destroy', function () {
          popoverButton.off('click');
          popoverButton = null;

          wrappedWindow.off('click', applyAndHide);
          wrappedWindow = null;
        });

        /**
         * Toggles the visibility of the popover. Used as an event callback.
         * @param {object} $event
         */
        function toggle($event) {
          $event.stopPropagation();

          if (scope.open) {
            hide();
          } else {
            el.css('display', 'block');
            recalculate();
            scope.open = true;
            wrappedWindow.on('click', applyAndHide);
          }
        }

        function applyAndHide() { scope.$apply(hide); }

        /**
         * Hides the popover and unbinds the window click listener.
         */
        function hide() {
          scope.open = false;

          //@TODO: Use $animation in 1.2.
          $timeout(function () { el.css('display', 'none'); }, 400);

          wrappedWindow.off('click', applyAndHide);
        }

        /**
         * Figures out the placement of the popover and applies it to the element's style.
         */
        function recalculate () {
          el.css('min-width', '');
          el.css(position.position(scope.placement, positioner));
        }
      }
    };
  }
]);
