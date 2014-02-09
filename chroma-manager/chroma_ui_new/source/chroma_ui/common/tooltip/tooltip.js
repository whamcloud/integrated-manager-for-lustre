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

  angular.module('iml-tooltip')
    .directive('imlTooltip', ['position', '$timeout', 'strategies', imlTooltip]);

  function imlTooltip(position, $timeout, strategies) {
    return {
      scope: {
        toggle: '=?',
        direction: '@'
      },
      restrict: 'E',
      transclude: true,
      replace: true,
      templateUrl: 'common/tooltip/assets/html/tooltip.html',
      link: function link(scope, jqElement) {
        var deregister;

        var jqPreviousEl = jqElement.prev();

        if (!jqPreviousEl.length) throw new Error('Previous element not found for tooltip!');

        var directions = _.values(position.DIRECTIONS),
          directionsJoined = directions.join(' ');

        directions.splice(directions.indexOf(scope.direction), 1);
        directions.unshift(scope.direction);

        scope.$on('$destroy', function onDestroy() {
          jqPreviousEl = null;
          deregister();
        });

        if (!scope.hasOwnProperty('toggle')) {
          deregister = strategies(jqPreviousEl, scope, {
            show: turnThenShow,
            hide: hide
          });
        } else {
          deregister = scope.$watch('toggle', function (newValue, oldValue) {
            if (newValue === oldValue) return;

            if (newValue)
              turnThenShow();
            else
              hide();
          }, true);
        }

        function turnThenShow() {
          $timeout(show);
        }

        function show() {
          setPosition();

          angular.element(position.$window).on('resize', throttledResize);
        }

        function hide() {
          delete scope.in;

          angular.element(position.$window).off('resize', throttledResize);
        }

        var throttledResize = _.throttle(function() {
          if (!jqElement.hasClass('in')) return;

          setPosition();
          scope.$digest();
        }, 500);

        /**
         * Sets the position of the tooltip by placing a clone until a match is found.
         */
        function setPosition() {
          var clone = jqElement[0].cloneNode(true),
            jqClone = angular.element(clone),
            clonePosition = position.positioner(clone),
            windowPosition = position.positioner(position.$window);

          jqClone.css('display', 'block');

          // place the clone.
          jqElement.after(clone);

          // check where clone fits.
          directions.some(function (direction) {
            delete scope.in;

            jqClone.removeClass(directionsJoined).addClass(direction);

            var calculatedClonePosition = position.position(direction, clonePosition);

            _.extend(clone.style, calculatedClonePosition);

            var fits = !position.overflows(direction, windowPosition, clonePosition);

            if (fits) {
              scope.placement = direction;
              scope.in = 'in';
              _.extend(jqElement[0].style, calculatedClonePosition);
            }

            return fits;
          });

          //destroy the clone
          jqClone.remove();
          clone = null;
          jqClone = null;
        }
      }
    };
  }
}());
