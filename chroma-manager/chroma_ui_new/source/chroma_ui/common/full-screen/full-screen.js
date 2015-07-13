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


  /**
   * @ngdoc directive
   * @name fullScreen:fullScreenBtn
   * @restrict A
   *
   * @description
   * When clicked this button will signal to fullScreen that the container element should be toggled
   * in fullscreen mode.
   *
   * @element ANY
   *
   * @example
     <example>
       <file name="index.html">
         <div class="full-screen">
           <button type="button" full-screen-btn></button>
           <p>This will go fullscreen</p>
         </div>
       </file>
     </example>
   */
  angular.module('fullScreen').directive('fullScreenBtn', function getDirective() {
    return {
      restrict: 'A',
      templateUrl: 'common/full-screen/assets/html/full-screen-button-text.html',
      require: '^fullScreen',
      link: function link(scope, wrappedEl, attrs, fullScreenCtrl) {
        scope.fullScreen = {
          open: false,
          text: function () {
            return this.open ? 'Exit Full Screen' : 'Full Screen';
          }
        };

        var applyAndToggleFullScreen = _.bind(scope.$apply, scope, toggleFullScreen);

        clickHandler('on');

        scope.$on('$destroy', _.partial(clickHandler, 'off'));

        /**
         * Toggles the fullscreen mode.
         */
        function toggleFullScreen() {
          scope.fullScreen.open = !scope.fullScreen.open;

          fullScreenCtrl.fullScreen(scope.fullScreen.open);
        }

        function clickHandler(type) {
          wrappedEl[type]('click', applyAndToggleFullScreen);
        }
      }
    };
  })
  /**
   * @ngdoc directive
   * @name fullScreen:fullScreen
   * @restrict C
   *
   * @description
   * This container communicates with a child fullScreenBtn to control the fullscreen mode.
   * Child directives can require this controller and register to be called when the fullscreen mode changes.
   *
   * @element ANY
   *
   * @example
     <example>
       <file name="index.html">
         <div class="full-screen">
           <button type="button" full-screen-btn></button>
           <p>This will go fullscreen</p>
         </div>
       </file>
     </example>
   */
  .directive('fullScreen', function getDirective() {
    return {
      restrict: 'C',
      controller: ['$element', '$scope', function FullScreenCtrl($element, $scope) {
        var body = angular.element('body'),
          fullScreenContainerClass = 'full-screen-container',
          listeners = [];

        /**
         * Restores the body class and kills the reference.
         */
        $scope.$on('$destroy', function onDestroy() {
          listeners.length = 0;

          body.removeClass(fullScreenContainerClass);
          body = null;
        });

        /**
         * Toggles fullscreen classes. Also calls registered fullscreen listeners.
         *
         * @param {Boolean} fullScreenMode Are we in full screen mode?
         */
        this.fullScreen = function fullScreen(fullScreenMode) {
          body.toggleClass(fullScreenContainerClass, fullScreenMode);
          $element.toggleClass('active', fullScreenMode);

          listeners.forEach(function (func) { func(fullScreenMode); });
        };

        /**
         * Adds a new listener to be called when the full screen mode changes.
         * @param {Function} func
         */
        this.addListener = function addListener (func) {
          listeners.push(func);
        };

        /**
         * Removes the func from listeners that are called when the full screen mode changes.
         * @param {Function} func
         */
        this.removeListener = function removeListener(func) {
          var index = listeners.indexOf(func);

          if (index !== -1) listeners.splice(index, 1);
        };
      }]
    };
  });
}());