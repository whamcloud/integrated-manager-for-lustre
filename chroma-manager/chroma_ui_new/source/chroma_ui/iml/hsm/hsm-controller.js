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


angular.module('hsm')
  .controller('HsmCtrl', ['$scope', '$modal', 'HsmCdtStream',
                          'HsmCopytoolStream', 'HsmCopytoolOperationStream',
                          'FileSystemStream', 'DURATIONS',
  function HsmCtrl($scope, $modal, HsmCdtStream, HsmCopytoolStream,
                   HsmCopytoolOperationStream, FileSystemStream, DURATIONS) {
    'use strict';

    $scope.hsm = {
      copytools: {objects: []},
      copytoolOperations: {objects: []},
      fileSystems: {objects: []},
      selectedFileSystem: null,
      data: [],
      onUpdate: function(unit, size) {
        hsmCdtStream.setDuration(unit, size);
      },
      options: {
        setup: function(chart, d3) {
          chart.useInteractiveGuideline(true);

          chart.forceY([0, 1]);

          chart.yAxis.tickFormat(d3.format('d'));

          chart.xAxis.showMaxMin(false);

          chart.color(['#F3B600', '#A3B600', '#0067B4']);
        }
      },
      unit: DURATIONS.MINUTES,
      size: 10
    };

    $scope.newCopytoolModal = function () {
      return $modal.open({
        templateUrl: 'iml/hsm/assets/html/new_copytool.html',
        controller: 'HsmCopytoolModalCtrl',
        backdrop: 'static',
        resolve: {
          fileSystems: function () {
            return $scope.hsm.fileSystems;
          }
        }
      }).result;
    };

    var fileSystemConstrainedStreams = [];

    // stream for chart data
    var hsmCdtStream = HsmCdtStream.setup('hsm.data', $scope);
    hsmCdtStream.setDuration($scope.hsm.unit, $scope.hsm.size);
    fileSystemConstrainedStreams.push(hsmCdtStream);

    // stream for copytool list
    var hsmCopytoolStream = HsmCopytoolStream.setup('hsm.copytools', $scope);
    hsmCopytoolStream.startStreaming();
    fileSystemConstrainedStreams.push(hsmCopytoolStream);

    // stream for copytoolOperation list
    var hsmCopytoolOperationStream = HsmCopytoolOperationStream.setup('hsm.copytoolOperations', $scope);
    hsmCopytoolOperationStream.startStreaming();
    fileSystemConstrainedStreams.push(hsmCopytoolOperationStream);

    // stream for fileSystems list
    var fileSystemStream = FileSystemStream.setup('hsm.fileSystems', $scope);
    fileSystemStream.startStreaming();

    // on filesystem selection changes, update the querystrings
    // of streams that can be filtered by filesystem
    $scope.onFileSystemSelection = function () {
      var params;

      // force the chart to refresh
      $scope.hsm.data.length = 0;

      if (!$scope.hsm.selectedFileSystem) {
        params = {};
      } else {
        params = {qs: {filesystem_id: $scope.hsm.selectedFileSystem.id}};
      }

      fileSystemConstrainedStreams.forEach(function (stream) {
        stream.updateParams(params);
      });
    };
  }
]);
