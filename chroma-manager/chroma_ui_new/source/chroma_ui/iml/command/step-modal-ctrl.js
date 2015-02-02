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


angular.module('command')
  .controller('StepModalCtrl', ['$scope', '$modalInstance', 'steps', 'job', 'throwIfError', 'COMMAND_STATES',
    function StepModalCtrl ($scope, $modalInstance, steps, job, throwIfError, COMMAND_STATES) {
      'use strict';

      $scope.$on('$destroy', function onDestroy () {
        steps.end();
        job.end();
      });

      $scope.stepModal = {
        steps: [],
        accordion0: true,
        /**
         * Closes the modal.
         */
        close: function close () {
          $modalInstance.close('close');
        },
        /**
         * Returns an adjective describing the state of the job.
         * @param {Object} job
         * @returns {String}
         */
        getJobAdjective: function getJobAdjective (job) {
          if (job.state === 'pending')
            return COMMAND_STATES.WAITING;

          if (job.state !== 'complete')
            return COMMAND_STATES.RUNNING;

          if (job.cancelled)
            return COMMAND_STATES.CANCELLED;
          else if (job.errored)
            return COMMAND_STATES.FAILED;
          else
            return COMMAND_STATES.SUCCEEDED;
        }
      };

      job.onValue('data', throwIfError(function onValue (response) {
        $scope.stepModal.job = response.body;
      }));

      steps.onValue('data', throwIfError(function onValue (response) {
        $scope.stepModal.steps = response.body.objects;
      }));
    }])
  .factory('openStepModal', ['$modal', function openStepModalFactory ($modal) {
    'use strict';

    var extractId = /\/api\/step\/(\d+)\/$/;

    /**
     * Opens the step modal to show information about
     * the provided job.
     * @param {Object} job
     * @returns {Object}
     */
    return function openStepModal (job) {
      return $modal.open({
        templateUrl: 'iml/command/assets/html/step-modal.html',
        controller: 'StepModalCtrl',
        windowClass: 'step-modal',
        backdrop: 'static',
        resolve: {
          /**
           * Resolves to a job spark.
           * @param {Function} requestSocket
           */
          job: ['requestSocket', function getJob (requestSocket) {
            var spark = requestSocket();
            spark.setLastData({ body: job });

            spark.sendGet('/job/' + job.id);

            return spark;
          }],
          /**
           * Resolves to a steps spark.
           * @param {Function} requestSocket
           */
          steps: ['requestSocket', function getSteps (requestSocket) {
            var stepIds = job.steps.map(function getId (step) {
              return step.replace(extractId, '$1');
            });

            var spark = requestSocket();

            spark.sendGet('/step', {
              qs: {
                id__in: stepIds,
                limit: 0
              }
            });

            return spark;
          }]
        }
      });
    };
  }]);
