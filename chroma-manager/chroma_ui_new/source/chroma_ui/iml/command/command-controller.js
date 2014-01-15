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


angular.module('command', [])
  .controller('CommandCtrl', ['$scope', '$modal', 'CommandModel',
  function CommandCtrl($scope, $modal, CommandModel) {
    'use strict';

    this.executeJob = function executeJob (victim, action) {
      var job = {class_name: action.class_name, args: action.args};
      var job_message = action.verb + '(' + victim.label + ')';
      function createApiCommand () {
        return CommandModel.save({jobs: [job], message: job_message});
      };

      if (action.confirmation) {
        $modal.open({
          templateUrl: 'iml/command/assets/html/confirmation.html',
          controller: 'CommandConfirmationModalCtrl',
          backdrop: 'static',
          resolve: {
            title: function () {
              return job_message;
            },
            confirmPrompts: function () {
              return [action.confirmation];
            }
          }
        }).result.then(createApiCommand);
      } else {
        createApiCommand();
      }
    };

    this.changeState = function changeState (victim, action) {
      var confirmPrompts = [];
      var requiresConfirmation = false;
      function runApiStateChange () {
        return victim.changeState(action.state);
      };

      victim.testStateChange(action.state)
      .then(function handleStateChange (data) {
        if (data.transition_job == null) {
          // no-op
          return;
        } else if (data.dependency_jobs.length > 0) {
          data.dependency_jobs.forEach(function (job) {
            confirmPrompts.push(job.description);

            if (job.requires_confirmation)
              requiresConfirmation = true;
          });
        } else if (data.transition_job.confirmation_prompt) {
          requiresConfirmation = true;
          confirmPrompts.push(data.transition_job.confirmation_prompt);
        } else {
          requiresConfirmation = data.transition_job.requires_confirmation;
        }

        if (requiresConfirmation) {
          $modal.open({
            templateUrl: 'iml/command/assets/html/confirmation.html',
            controller: 'CommandConfirmationModalCtrl',
            backdrop: 'static',
            resolve: {
              title: function () {
                return data.transition_job.description;
              },
              confirmPrompts: function () {
                return confirmPrompts;
              }
            }
          }).result.then(runApiStateChange);
        } else {
          runApiStateChange();
        }
      });
    };

    $scope.onActionSelection = function onActionSelection (victim, action) {
      if (action.class_name) {
        this.executeJob(victim, action);
      } else {
        this.changeState(victim, action);
      }
    }.bind(this);
  }])
  .controller('CommandConfirmationModalCtrl', ['$scope', '$q', '$modalInstance',
                                               'title', 'confirmPrompts',
  function CommandConfirmationModalCtrl($scope, $q, $modalInstance,
                                        title, confirmPrompts) {
    'use strict';

    $scope.title = title;
    $scope.confirmPrompts = confirmPrompts;

    $scope.onConfirm = function onConfirm () {
      $modalInstance.close();
    };
    $scope.onCancel = function onCancel () {
      $modalInstance.dismiss('cancel');
    };
  }
]);
