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


angular.module('action-dropdown-module').factory('handleAction',
  ['requestSocket', 'openConfirmActionModal', function handleActionFactory (requestSocket, openConfirmActionModal) {
    'use strict';

    /**
     * Performs the given action
     * @param {Object} record
     * @param {Object} action
     */
    return function handleAction (record, action) {
      var socket = requestSocket();

      var method;

      if (action.class_name)
        method = executeJob;
      else if (action.param_key)
        method = setConfParam;
      else
        method = changeState;

      return method(socket, record, action);
    };

    /**
     * Executes a job on a record.
     * @param {Object} socket
     * @param {Object} record
     * @param  {Object} action
     * @returns {Object}
     */
    function executeJob (socket, record, action) {
      var jobMessage = '%s(%s)'.sprintf(action.verb, record.label);

      var jobSender = sendJob(socket, {
        json: {
          jobs: [_.pick(action, 'class_name', 'args')],
          message: jobMessage
        }
      });

      if (action.confirmation)
        return openConfirmActionModal(jobMessage, [action.confirmation])
          .result
          .then(mightSkip(jobSender));
      else
        return jobSender();
    }

    /**
     * HOF. Sends the job.
     * @param {Object} socket
     * @param {Object} data
     * @returns {Function}
     */
    function sendJob (socket, data) {
      return function send () {
        return socket.sendPost('/command', data, true)
          .catch(throwError);
      };
    }

    /**
     * Executes a state change on a record.
     * @param {Object} socket
     * @param {Object} record
     * @param {Object} action
     * @returns {Object}
     */
    function changeState (socket, record, action) {
      return socket
        .sendPut(record.resource_uri, {
          json: {
            dry_run: true,
            state: action.state
          }
        }, true)
        .catch(throwError)
        .then(function introspectDryRun (response) {
          var data = response.body;

          if (data.transition_job == null)
            return;

          var requiresConfirmation;
          var confirmPrompts = [];

          if (data.dependency_jobs.length > 0) {
            confirmPrompts = data.dependency_jobs.map(function buildPrompts (job) {
              if (job.requires_confirmation)
                requiresConfirmation = true;

              return job.description;
            });
          } else if (data.transition_job.confirmation_prompt) {
            requiresConfirmation = true;
            confirmPrompts.push(data.transition_job.confirmation_prompt);
          } else {
            requiresConfirmation = data.transition_job.requires_confirmation;
          }

          var stateChanger = sendStateChange(socket, record.resource_uri, action.state);

          if (requiresConfirmation)
            return openConfirmActionModal(data.transition_job.description, confirmPrompts)
              .result
              .then(mightSkip(stateChanger));
          else
            return stateChanger();
        });
    }

    /**
     * HOF. Sends the state change.
     * @param {Object} socket
     * @param {String} path
     * @param {String} state
     * @returns {Function}
     */
    function sendStateChange (socket, path, state) {
      return function sendChange () {
        return socket.sendPut(path, {
          json: { state: state }
        }, true)
          .catch(throwError);
      };
    }

    /**
     * Sets a conf param key value pair and sends it.
     * @param {Object} socket
     * @param {Object} record
     * @param {Object} action
     * @returns {Object}
     */
    function setConfParam (socket, record, action) {
      record = action.mdt;

      record.conf_params[action.param_key] = action.param_value;

      var path = '/%s/%s'.sprintf(record.resource, record.id);

      return socket.sendPut(path, {
        json: record
      }, true)
        .catch(throwError);
    }

    /**
     * HOF. Skips the command modal if the user specifies.
     * @param {Function} func
     * @returns {Function}
     */
    function mightSkip (func) {
      return function skipHandler (skips) {
        return func()
          .then(function checkSkip (data) {
            if (!skips)
              return data;
          });
      };
    }

    /**
     * Throws response.error.
     * @param {Object} response
     */
    function throwError (response) {
      throw response.error;
    }
  }]
);
