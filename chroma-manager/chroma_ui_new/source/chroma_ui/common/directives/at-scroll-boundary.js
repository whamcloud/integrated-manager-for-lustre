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


/**
 * This directive detects whether an element has hit it's scroll boundary in a particular direction.
 *
 * It attaches a boolean hitBoundary property to the scope to indicate whether we are at the boundary. If oneHit is
 * passed as an attribute, once the boundary is hit the hitBoundary property will stay true.
 *
 * @example <div atScrollBoundary direction="bottom" oneHit="true"></div>
 * @name atScrollBoundary
 *
 */
angular.module('atScrollBoundary').directive('atScrollBoundary', function factory() {
  'use strict';

  var BOTTOM = 'bottom';

  return {
    restrict: 'A',
    link: function postLink(scope, el, attrs) {
      _.defaults(scope, {scrollDirection: BOTTOM, hitBoundary: false});

      var oneHit = scope.$eval(attrs.oneHit);
      var unwrappedEl = el[0];

      //@TODO: Add other directions as needed.
      var directions = {};
      directions[BOTTOM] = function isAtBottom() {
        return unwrappedEl.scrollTop + unwrappedEl.clientHeight >= unwrappedEl.scrollHeight - 20;
      };

      var scrollFunc = scope.$apply.bind(scope, function onScroll() {
        scope.hitBoundary = (directions[scope.scrollDirection] || angular.identity.bind(null, false))();

        if (oneHit && scope.hitBoundary) {
          cleanup();
        }
      });

      function cleanup() {
        if (unwrappedEl)
          unwrappedEl.removeEventListener('scroll', scrollFunc, true);

        unwrappedEl = null;
      }

      unwrappedEl.addEventListener('scroll', scrollFunc, true);

      scope.$on('$destroy', cleanup);
    }
  };
});
