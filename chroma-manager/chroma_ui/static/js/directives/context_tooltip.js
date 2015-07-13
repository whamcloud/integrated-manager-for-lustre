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

  var contextTooltipName = 'contextTT';
  function nameSuffix(suffix) { return contextTooltipName + suffix; }

  function factory($tooltip, HELP_TEXT) {
    return {
      restrict: 'A',
      scope: true,
      link: function postLink(scope, el, attrs) {
        attrs.$observe('contextTooltip', function (value) {
          attrs.$set(contextTooltipName, HELP_TEXT[value]);
        });

        $tooltip(contextTooltipName, 'tooltip', 'mouseenter').link(scope, el, attrs);
      }
    };
  }

  /**
   * @description Service wrapper for Context Tooltips. Useful for testing.
   * @name contextTooltipService
   */
  angular.module('services').factory('contextTooltipService', ['$tooltip', 'HELP_TEXT', factory]);

  /**
   * Adds a tooltip
   * @name contextTooltip
   * @example
   * <a context-tooltip="tooltip_name" tooltip-placement="right"></a>
   * @see {@link http://angular-ui.github.io/bootstrap/#/tooltip|Tooltip Options}
   */
  angular.module('directives').directive('contextTooltip', ['contextTooltipService', angular.identity]);

  /**
   * @description Interfaces with the tooltip directive to render the correct tooltip.
   */
  angular.module('directives').directive(nameSuffix('Popup'), function () {
    return {
      restrict: 'E',
      replace: true,
      scope: { content: '@', placement: '@', animation: '&', isOpen: '&' },
      templateUrl: 'template/tooltip/tooltip-html-unsafe-popup.html'
    };
  });
}());
