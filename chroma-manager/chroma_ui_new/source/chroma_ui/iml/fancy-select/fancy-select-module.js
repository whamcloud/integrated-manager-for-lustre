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

  angular.module('fancy-select', [])
    .directive('fancySelectBox', [function fancySelectBoxDirective () {
      return {
        restrict: 'EA',
        replace: true,
        scope: {
          data: '=',
          onSelected: '&'
        },
        templateUrl: 'iml/fancy-select/assets/html/fancy-select.html',
        link: function link (scope) {
          var off = scope.$watch('data', function setupScope (newData) {
            if (_.isEmpty(newData))
              return;
            scope.onSelected({item: scope.data[0]});
            scope.fancy.selected = scope.data[0];

            off();
          });

          scope.fancy = {
            /**
             * Selects the selected item to be selected on the scope
             * @param {Object} item
             */
            selectItem: function selectItem (item) {
              scope.fancy.selected = item;
              scope.onSelected({item: item});
            },
            /**
             * Called when the drop down is toggled. It sets the value of "open" on the scope.
             * @param {Boolean} open
             */
            onToggle: function onToggle (open) {
              scope.fancy.open = open;
            }
          };
        }
      };
    }]);
})();
