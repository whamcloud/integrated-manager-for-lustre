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


angular.module('command')
  .controller('JobTreeCtrl', ['$scope', 'getJobSpark', 'GROUPS', 'openStepModal', 'throwIfError',
    function JobTreeCtrl ($scope, getJobSpark, GROUPS, openStepModal, throwIfError) {
      'use strict';

      var pendingTransitions = [];

      $scope.jobTree = {
        GROUPS: GROUPS,
        jobs: [],
        openStep: function openStep (job) {
          openStepModal(job);
        },
        showTransition: function showTransition (job) {
          return job.available_transitions.length > 0 && pendingTransitions.indexOf(job.id) === -1;
        },
        doTransition: function doTransition (job, newState) {
          job.state = newState;

          pendingTransitions.push(job.id);

          spark.sendPut(job.resource_uri, { json: job }, throwIfError(function ack () {
            pendingTransitions.splice(pendingTransitions.indexOf(job.id), 1);
          }));
        }
      };

      $scope.$on('$destroy', function onDestroy () {
        spark.end();
      });

      var spark = getJobSpark();

      spark.sendGet('/job', {
        qs: {
          id__in: $scope.command.jobIds,
          limit: 0
        }
      });

      spark.onValue('pipeline', function onValue (response) {
        $scope.jobTree.jobs = response.body;
      });
    }])
  .factory('getJobSpark', ['requestSocket', 'jobTree', 'throwIfError',
    function getJobSparkFactory (requestSocket, jobTree, throwIfError) {
      'use strict';

      /**
       * Returns a spark with a convert to tree pipe added.
       * @returns {Object}
       */
      return function getJobSpark () {
        var spark = requestSocket();

        /**
         * Converts the jobs to a dependency tree.
         * @param {Object} response
         */
        spark.addPipe(throwIfError(function convertToTree (response) {
          response.body = jobTree(response.body.objects);

          return response;
        }));

        return spark;
      };
    }
  ]);
