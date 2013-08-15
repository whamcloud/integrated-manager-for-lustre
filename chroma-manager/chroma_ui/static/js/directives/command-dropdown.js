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

  function factory(STATIC_URL, $window) {
    return {
      restrict: 'A',
      scope: {
        placement: '@commandPlacement',
        data: '=commandData'
      },
      templateUrl: '%spartials/directives/command_dropdown.html'.sprintf(STATIC_URL),
      link: function postLink(scope, el) {

        /**
         * @description builds the list of actions that can be performed.
         */
        function buildList() {
          scope.list = ['transitions', 'jobs']
            .map(function (type) {
              var items = angular.copy(scope.data['available_%s'.sprintf(type)]);

              items
                .filter(function (item) {
                  return item.verb !== null;
                })
                .forEach(function (item) {
                item.type = type;
              });

              return items;
            })
            .reduce(function (prev, curr) {
              return prev.concat(curr);
            });
        }

        /**
         * @description creates event handlers. Proxies the call to LiveObject.
         * @param {string} type
         */
        function generateHandler(type) {
          var handlerName = '%sClicked'.sprintf(type);
          scope[handlerName] = function ($event) {
            $window.LiveObject[handlerName].apply($event.target);
          };
        }

        scope.toJson = angular.toJson;

        var deregistrationFunctions = [];

        deregistrationFunctions[0] = scope.$on('disableCommandDropdown', function (ev, uri) {
          if (scope.data.resource_uri === uri) {
            el.addClass('hide');
          }
        });

        deregistrationFunctions[1] = scope.$on('updateCommandDropdown', function (ev, uri, obj) {
          function runUpdate() {
            scope.data = obj;
            buildList();
          }

          if (scope.data.resource_uri === uri) {
            el.removeClass('hide');

            scope.$root.safeApply(runUpdate, scope);
          }
        });

        // Setup handlers.
        generateHandler('transition');
        generateHandler('job');

        // Build the list the first time.
        buildList();

        // Blank out the button if a job is in progress
        if ($window.CommandNotification.uriIsWriteLocked(scope.data.resource_uri)) {
          scope.$broadcast('disableCommandDropdown', scope.data.resource_uri);
        }

        scope.$on('$destroy', function () {
          deregistrationFunctions.forEach(function (func) { func(); });
        });
      }
    };
  }

  /**
   * @description Service wrapper for the command dropdown. Useful for testing.
   * @name commandDropdownService
   */
  angular.module('services').factory('commandDropdownService', ['STATIC_URL', '$window', factory]);

  /**
   * @description Generates a dropdown based on a given resource.
   * @name commandDropdown
   * @example
   * <div command-dropdown command-placement="right" command-data="((data))"></div>
   */
  angular.module('directives').directive('commandDropdown', ['commandDropdownService', angular.identity]);
}());
