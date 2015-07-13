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


(function (_) {
  'use strict';

  function remoteValidateFormFactory() {
    return {
      restrict: 'A',
      scope: true,
      controller: ['$scope', '$element', function ($scope, $element) {
        var formController = $element.controller('form');

        if (formController === undefined) {
          throw new Error('formController not found, needed by remote-validate-form');
        }

        this.components = {
          '__all__': formController
        };

        // We don't need element anymore. Kill the reference.
        $element = null;

        /**
         * Adds a new component to the object literal.
         * @name registerComponent
         * @param {string} name The Name of the component.
         * @param {object} ngModel The model bound to the component.
         * @type {function}
         */
        this.registerComponent = function (name, ngModel) {
          this.components[name] = ngModel;
        }.bind(this);

        /**
         * Returns the component if it exists.
         * @type {function}
         * @returns {ngModel|undefined}
         */
        this.getComponent = function (name) {
          return this.components[name];
        }.bind(this);

        /**
         * Sets all registered components to a valid state.
         * Also deletes error message associated with that component.
         * @type {function}
         */
        this.resetComponentsValidity = function () {
          _(this.components).forEach(function (component, name) {
            component.$setValidity('server', true);
            delete $scope.serverValidationError[name];
          });
        }.bind(this);

        $scope.$on('$destroy', function () {
          this.components = null;
        }.bind(this));
      }],
      link: function (scope, el, attrs, formController) {
        scope.serverValidationError = {};

        var thenLocation = attrs.remoteThen;

        /**
         * Abstracts common code from success and errback functions.
         * @param [func]
         * @returns {Function}
         */
        function callbackBuilder (func) {
          return function callback (resp) {
            formController.resetComponentsValidity();

            (func || angular.noop)(resp);

            return resp;
          };
        }

        /**
         * Called when a remote request succeeds.
         * @type {Function}
         */
        var success = callbackBuilder();

        /**
         * called when a remote request fails.
         * @type {Function}
         */
        var errback = callbackBuilder(function errbackCallback (resp) {
          _(resp.data).forEach(function (errorList, field) {
            var component = formController.getComponent(field);

            if (component) {
              if (_.isString(errorList)) {
                errorList = [errorList];
              }

              component.$setValidity('server', false);
              scope.serverValidationError[field] = errorList;
            }
          });
        });

        var deregisterWatch = scope.$watch(thenLocation, function thenWatcher(newThen, oldThen) {
          if (newThen === oldThen) {
            return;
          }

          newThen(success, errback);
        });

        scope.$on('$destroy', function () {
          scope.serverValidationError = null;
          deregisterWatch();
        });
      }
    };
  }

  function remoteValidateComponentFactory() {
    return {
      require: ['^remoteValidateForm', 'ngModel'],
      restrict: 'A',
      link: function (scope, el, attrs, ctrls) {
        var formController = ctrls[0];
        var ngModel = ctrls[1];
        formController.registerComponent(attrs.name, ngModel);
      }
    };
  }

  /**
   * Service wrapper for remote validation of a form. Useful for testing.
   * @name remoteValidateFormService
   */
  angular.module('services').factory('remoteValidateFormService', [remoteValidateFormFactory]);

  /**
   * Service wrapper for remote validation of a form component. Useful for testing.
   * @name remoteValidateComponentFactory
   */
  angular.module('services').factory('remoteValidateComponentService', [remoteValidateComponentFactory]);

  /**
   * Registers a form as having remote validation.
   * @name remoteValidateForm
   */
  angular.module('directives')
    .directive('remoteValidateForm', ['remoteValidateFormService', angular.identity]);

  /**
   * Registers a form component as needing validation.
   * Use inside the remoteValidateForm directive,
   * @name remoteValidateFormComponent
   */
  angular.module('directives')
    .directive('remoteValidateComponent', ['remoteValidateComponentService', angular.identity]);
}(window.lodash));
