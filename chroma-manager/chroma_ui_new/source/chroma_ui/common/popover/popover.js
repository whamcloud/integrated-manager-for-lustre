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


angular.module('iml-popover', ['position']).directive('imlPopover', ['position', '$timeout', '$window', '$compile',
  function (position, $timeout, $window, $compile) {
    'use strict';

    var template = '<div class="popover fade {{ placement }}" ng-class="{in: open}">\
<div class="arrow"></div>\
<h3 class="popover-title" ng-bind="title" ng-show="title"></h3>\
<div class="popover-content"></div>\
</div>';

    return {
      restrict: 'E',
      transclude: true,
      scope: {
        placement: '@',
        title: '@',
        work: '&',
        onToggle: '&'
      },
      link: function link (scope, el, attrs, ctrl, $transclude) {
        var popoverLinker = $compile(template);

        var popoverButton = el.siblings('.activate-popover').eq(0),
          wrappedWindow = angular.element($window);

        if (!popoverButton) throw new Error('No popover button found.');

        scope.open = false;

        scope.work({
          actions: {
            hide: hide,
            recalculate: recalculate
          }
        });

        popoverButton.on('click', function handleClick ($event) {
          // Close any other popovers that are currently open
          if (!scope.open)
            wrappedWindow.trigger('click');

          toggle($event);
          scope.$digest();
        });

        scope.$on('$destroy', function onDestroy () {
          popoverButton.off('click');
          wrappedWindow.off('click', digestAndHide);
          wrappedWindow = popoverButton = popoverLinker = null;

          destroyPopover();
        });

        var inheritedScope, popoverEl, positioner;
        function createPopover () {
          $transclude(function createNewPopover (clone, transcludedScope) {
            inheritedScope = transcludedScope;

            popoverEl = popoverLinker(scope, angular.noop);

            positioner = position.positioner(popoverEl[0]);

            popoverEl.find('.popover-content').append(clone);
            popoverEl.on('click', function handleClick ($event) {
              $event.stopPropagation();
            });

            el.before(popoverEl);

            scope.onToggle({
              state: 'opened'
            });

            $timeout(function showAndRecalculate () {
              transcludedScope.$parent.$digest();
              popoverEl.css('display', 'block');

              if (scope.placement)
                recalculate();

              scope.open = true;
              scope.$digest();
            }, 0, false);
          });
        }

        function destroyPopover () {
          scope.onToggle({
            state: 'closed'
          });

          if (popoverEl) {
            popoverEl.off('click');
            popoverEl.remove();
            popoverEl = null;
          }

          if (inheritedScope) {
            inheritedScope.$destroy();
            inheritedScope = null;
          }
        }

        /**
         * Toggles the visibility of the popover. Used as an event callback.
         * @param {object} $event
         */
        function toggle ($event) {
          $event.stopPropagation();

          if (scope.open) {
            hide();
          } else {
            createPopover();
            wrappedWindow.on('click', digestAndHide);
          }
        }

        function digestAndHide () {
          hide();
          scope.$digest();
        }

        /**
         * destroys the popover and unbinds the window click listener.
         */
        function hide () {
          scope.open = false;

          $timeout(destroyPopover, 500);

          wrappedWindow.off('click', digestAndHide);
        }

        /**
         * Figures out the placement of the popover and applies it to the element's style.
         */
        function recalculate () {
          if (!popoverEl)
            return;

          popoverEl.css('min-width', '');
          popoverEl.css(position.position(scope.placement, positioner));
        }
      }
    };
  }
]);
