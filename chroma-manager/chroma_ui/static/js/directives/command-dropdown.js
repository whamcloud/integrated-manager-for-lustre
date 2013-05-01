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

  function factory(STATIC_URL, helpText, $window) {
    return {
      restrict: 'A',
      scope: {
        placement: '@commandPlacement',
        data: '=commandData'
      },
      templateUrl: '%spartials/directives/command_dropdown.html'.sprintf(STATIC_URL),
      link: function postLink(scope, el) {
        var maps = {
          // resource type + state mapping to contextual help
          transitionsHelp: {
            filesystem: {
              stopped: '_stop_file_system',
              removed: '_remove_file_system',
              available: '_start_file_system'
            },
            host: {
              lnet_up: '_start_lnet',
              lnet_down: '_stop_lnet',
              removed: '_remove_server',
              lnet_unloaded: '_unload_lnet'
            },
            'target-MGT': {
              unmounted: '_stop_mgt',
              mounted: '_start_mgt',
              removed: '_remove_mgt'
            },
            'target-MDT': {
              unmounted: '_stop_mdt',
              mounted: '_start_mdt'
            },
            'target-OST': {
              unmounted: '_stop_ost',
              mounted: '_start_ost',
              removed: '_remove_ost'
            }
          },
          // resource type + job class name mapping to contextual help
          jobsHelp: {
            host: {
              ForceRemoveHostJob: '_force_remove'
            }
          }
        };

        var resourceType = $window.LiveObject.resourceType(scope.data);

        /**
         * @description builds the list of actions that can be performed.
         */
        function buildList() {
          scope.list = ['transitions', 'jobs']
            .map(function (type) {
              var items = angular.copy(scope.data['available_%s'.sprintf(type)]);
              var mapType = '%sHelp'.sprintf(type);
              var topics = maps[mapType][resourceType] || {};

              items.forEach(function (item) {
                item.type = type;
                item.tooltip = helpText(topics[item.state || item.class_name]);
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
            $window.LiveObject[handlerName].apply($event.srcElement);
          };
        }

        scope.toJson = angular.toJson;

        scope.$on('disableCommandDropdown', function (ev, uri) {
          if (scope.data.resource_uri === uri) {
            el.addClass('hide');
          }
        });

        scope.$on('updateCommandDropdown', function (ev, uri, obj) {
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
      }
    };
  }

  /**
   * @description Service wrapper for the command dropdown. Useful for testing.
   * @name commandDropdownService
   */
  angular.module('services').factory('commandDropdownService', ['STATIC_URL', 'helpText', '$window', factory]);

  /**
   * @description Generates a dropdown based on a given resource.
   * @name commandDropdown
   * @example
   * <div command-dropdown command-placement="right" command-data="((data))"></div>
   */
  angular.module('directives').directive('commandDropdown', ['commandDropdownService', angular.identity]);
}());
