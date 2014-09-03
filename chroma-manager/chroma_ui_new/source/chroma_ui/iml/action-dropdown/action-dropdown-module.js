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


angular.module('action-dropdown-module', ['socket-module'])
  .directive('actionDropdown', ['$q', 'handleAction', 'openCommandModal',
    function actionDropdown ($q, handleAction, openCommandModal) {
      'use strict';

      return {
        scope: {
          record: '='
        },
        restrict: 'E',
        replace: true,
        templateUrl: 'iml/action-dropdown/assets/html/action-dropdown.html',
        link: function link (scope, el, attrs) {
          scope.actionDropdown = {
            tooltipPlacement: (attrs.tooltipPlacement != null ? attrs.tooltipPlacement : 'left'),
            actionsProperty: (attrs.actionsProperty != null ? attrs.actionsProperty : 'available_actions'),
            disabled: false,
            /**
             * perform an action on the provided record.
             * @param {Object} record
             * @param {Object} action
             */
            handleAction: function runHandleAction (record, action) {
              var setTrue = setOpenFlag(true);
              var setFalse = setOpenFlag(false);

              setTrue();

              handleAction(record, action)
                .then(function mightOpenCommandModal (data) {
                  if (data)
                    return openCommandModal({
                      body: {
                        objects: [data.body.command || data.body]
                      }
                    })
                      .result;
                })
                .finally(setFalse);
            }
          };

          scope.$watch('record.locks.write', function watchWriteLock (newVal) {
            scope.actionDropdown.disabled = newVal.length > 0;
          });

          function setOpenFlag (state) {
            return function openFlag () {
              scope.actionDropdown.confirmOpen = state;
            };
          }
        }
      };
    }
  ])
  .filter('groupActions', [function groupActionsFilter () {
    'use strict';

    /**
     * Sort items by display_group, then by display_order.
     * Mark the last item in each group
     * @param {Array} input
     * @returns {Array}
     */
    return function groupActions (input) {
      if (_.pluck(input, 'display_group').length === 0)
        return input;

      var sorted = input.sort(function (a, b) {
        var x = a.display_group - b.display_group;
        return (x === 0 ? a.display_order - b.display_order : x);
      });

      sorted.forEach(function (item, index) {
        var next = sorted[index + 1];

        if (next && item.display_group !== next.display_group)
          item.last = true;
      });

      return sorted;
    };
  }]);
