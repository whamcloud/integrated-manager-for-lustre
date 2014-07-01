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


(function () {
  'use strict';

  //@TODO: This module is a stopgap. Remove when directives can be natively interpreted.

  function factory($rootScope, $compile) {
    return {
      /**
       * @description Abstraction to integrate the command-dropdown with datatables.
       * @param {number} index
       * @param {function} [transformFunc]
       * @param {function} [abortFunc]
       * @param {function} [commandClick]
       * @returns {function}
       */
      dataTableCallback: function (index, transformFunc, abortFunc, commandClick) {
        transformFunc = transformFunc || angular.identity;
        abortFunc = abortFunc || function () { return false; };

        /**
         * @description Called after a row draw. A good place to hook in.
         * @param {Object} row
         * @param {Object} data
         * @returns {[]}
         */
        return function fnRowCallback(row, data) {
          data = transformFunc(data);

          if (abortFunc(data)) {
            return row;
          }

          // NOTE: This is only being done because of the Angular in Backbone paradigm.
          var $actionCell = angular.element(row).find('td:nth-child(%d)'.sprintf(index));

          this.generateDropdown($actionCell, data, null, commandClick);

          return row;
        }.bind(this);
      },
      /**
       * @description The main core of this module. Takes an element and generates a command-dropdown directive
       * @param {object} parentOrElement The parent to insert into or the element itself
       * @param {object} data The data to attach to scope.
       * @param {string} [placement] What direction? 'top'|'bottom'|'left'|'right'
       * @param {Function} [commandClick] Passes the commandClick to the directive.
       * @returns {object} The command-dropdown element
       */
      generateDropdown: function (parentOrElement, data, placement, commandClick) {
        placement = placement || 'left';

        var isElement = (parentOrElement.attr('command-dropdown') !== undefined &&
          parentOrElement.attr('command-dropdown') !== false);

        var hasCommandClick =  (typeof commandClick === 'function');

        var template = (isElement ?
          parentOrElement:
          '<div command-dropdown command-placement="%s" command-data="data"%s></div>'.sprintf(
            placement,
            hasCommandClick ? ' command-click="commandClick($event, data, done)"': ''
          ));

        var insertfunc = (isElement ? angular.noop: function (fragment) { parentOrElement.html(fragment); });

        // NOTE: This is only being done because of the Angular in Backbone paradigm.
        var $scope = $rootScope.$new();

        $scope.data = data;

        if (hasCommandClick)
          $scope.commandClick = commandClick;

        return $scope.safeApply(function () {
          var link = $compile(template);
          var fragment = link($scope);
          insertfunc(fragment);

          return fragment.bind('$destroy', function () {
            $scope.safeApply(function () { $scope.$destroy(); }, $scope);

            fragment.unbind('$destroy');
          });
        }, $scope);
      }
    };
  }

  angular.module('services').factory('generateCommandDropdown', ['$rootScope', '$compile', factory]);
}());
