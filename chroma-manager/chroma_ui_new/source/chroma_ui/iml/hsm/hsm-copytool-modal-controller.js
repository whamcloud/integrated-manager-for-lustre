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


angular.module('hsm')
  .controller('HsmCopytoolModalCtrl', ['$scope', '$q', '$modalInstance',
                                       'stream', 'replaceTransformer',
                                       'HsmCopytoolModel', 'fileSystems',
  function HsmCopytoolModalCtrl($scope, $q, $modalInstance, stream, replaceTransformer, HsmCopytoolModel, fileSystems) {
    'use strict';
    var requiredFields = ['filesystem', 'host', 'bin_path', 'mountpoint', 'archive'];
    var dismiss = $modalInstance.dismiss.bind($modalInstance, 'cancel');
    $scope.fileSystems = fileSystems;
    $scope.workers = {objects: []};
    $scope.copytool = {
      filesystem: fileSystems.objects[0],
      host: $scope.workers.objects[0],
      archive: 1
    };
    $scope.onSubmit = function submitCopytool (copytool) {
      copytool.filesystem = copytool.filesystem.resource_uri;
      copytool.host = copytool.host.resource_uri;
      this.validate = HsmCopytoolModel.save(copytool).$promise
      .then(dismiss)
      .catch(function (reason) {
        return $q.reject(reason);
      });
    };
    $scope.onClose = dismiss;
    $scope.missingRequiredValues = function () {
      return requiredFields.filter(function (field) {
        return $scope.copytool[field] == null;
      }).length > 0;
    };
    $scope.isEmpty = function (object) {
      return angular.equals({}, object);
    };

    // stream for workers
    var hsmWorkerStream = stream('host', 'httpGetList', {
      params: {
        qs: {
          worker: true
        }
      },
      transformers: [replaceTransformer]
    }).setup('workers', $scope);
    hsmWorkerStream.startStreaming();

    // set default worker when the stream has data
    $scope.$watchCollection('workers.objects', function (workers) {
      if (!$scope.copytool.host && workers.length >= 0) {
        $scope.copytool.host = workers[0];
      }
    });
  }
]);
