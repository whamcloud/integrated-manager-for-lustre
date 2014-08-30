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

  angular.module('pdsh-module', ['pdsh-parser-module', 'iml-tooltip'])
    .directive('pdsh', ['pdshParser', pdsh]);

  /**
   * The pdsh directive.
   * @param {Object} pdshParser The pdsh parser service
   * @returns {Object}
   */
  function pdsh (pdshParser) {
    return {
      scope: {
        pdshChange: '&',
        pdshRequired: '=?',
        pdshLabel: '=?',
        pdshTooltip: '=?'
      },
      restrict: 'E',
      templateUrl: 'common/pdsh/assets/html/pdsh.html',
      replace: true,
      require: '^form',
      link: function (scope, elm, attrs, ctrl) {
        var states = {
          NEUTRAL: '',
          SUCCESS: 'has-success',
          ERROR: 'has-error'
        };
        var parsedState = states.NEUTRAL;
        var errorMessages = '';
        var hostnames = [];
        var parsedExpression;

        if (!scope.pdshLabel)
          scope.pdshLabel = 'Hostname';
        if (!scope.pdshTooltip)
          scope.pdshTooltip = 'The name of the host on your network. Takes a hostname or a PDSH expression.';

        // Handle updating the validity of the directive when the view changes.
        ctrl.pdsh.$parsers.unshift(updateModelAndValidity);

        /**
         * Sets the validity of the directive based on the pdsh expression being passed in.
         * @param {String} value
         * @returns {String|undefined}
         */
        function updateModelAndValidity (value) {
          scope.pdsh.parseExpression(value);

          if (_.isEmpty(value) || parsedState === states.SUCCESS) {
            ctrl.pdsh.$setValidity('pdsh', true);
            return value;
          } else {
            ctrl.pdsh.$setValidity('pdsh', false);
            return undefined;
          }
        }

        scope.pdsh = {
          /**
           * Parses the expression and calls the pdshChange function on the isolate scope. It also sets the view value
           * on the ngModel.
           * @param {String} pdshExpression
           */
          parseExpression: function parseExpression(pdshExpression) {
            parsedExpression = pdshParser(pdshExpression);

            if ('errors' in parsedExpression && pdshExpression.length > 0) {
              parsedState = states.ERROR;
              hostnames = [];
              errorMessages = parsedExpression.errors;
            }
            else if (pdshExpression.length > 0) {
              parsedState = states.SUCCESS;
              hostnames = parsedExpression.expansion;
            }
            else {
              parsedState = states.NEUTRAL;
              hostnames = [];
            }
          },
          sendChange: function sendChange () {
            scope.pdshChange({pdsh: pdsh.expression, hostnames: hostnames});
          },
          /**
           * Returns the error messages regarding the validity of the expression.
           * @returns {string}
           */
          getErrorMessages: function getErrorMessages () {
            return errorMessages;
          },
          /**
           * Returns the host names expanded by the expression.
           * @returns {Array}
           */
          getHostnames: function getHostnames () {
            return hostnames;
          },
          pdshForm: ctrl
        };
      }
    };
  }
}());
