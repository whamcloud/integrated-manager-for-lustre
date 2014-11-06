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
// express and approved by Intel in writing.=

angular.module('command')
  .factory('waitForCommandCompletion', ['COMMAND_STATES', 'createCommandSpark', '$q', 'openCommandModal',
    function waitForCommandCompletion (COMMAND_STATES, createCommandSpark, $q, openCommandModal) {
      'use strict';

      /**
       * HOF - returns a function that is used to make sure all commands complete before resolving
       * the promise.
       * @param {Boolean} showModal
       * @returns {Function}
       */
      return function waitForCommandCompletionService (showModal) {

        /**
         * Waits for the commands to complete and then resolves the returned promise with the
         * original response that was passed in and ends the spark.
         * @param {Object} response
         * @returns {Object} A promise that resolves when all commands finish.
         */
        return function waitForCommandsToComplete (response) {
          if (_.compact(response.body.errors).length)
            throw new Error(JSON.stringify(response.body.errors));

          var commands = _(response.body.objects).pluck('command').compact().value();

          var deferred = $q.defer();
          var commandSpark;
          if (commands.length) {
            commandSpark = createCommandSpark(commands);

            if (showModal) openCommandModal(commandSpark);

            commandSpark.onValue('pipeline', function onPipe (resp) {
              // response.body or response.body.objects
              // Normalize to array
              var commands = (!resp.body.objects) ? [resp.body] : resp.body.objects;
              var isCommandListComplete = commands.every(function (command) {
                return command.state !== COMMAND_STATES.PENDING;
              });

              if (isCommandListComplete) {
                commandSpark.end();
                deferred.resolve(response);
              }
            });
          } else {
            deferred.resolve(response);
          }

          return deferred.promise;
        };
      };
    }]);
