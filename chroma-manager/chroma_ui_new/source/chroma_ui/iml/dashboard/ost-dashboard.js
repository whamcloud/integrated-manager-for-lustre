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


(function () {
  'use strict';

  angular.module('dashboard').controller('OstDashboardCtrl', ['$scope', 'streams', 'dashboardPath', OstDashboardCtrl]);

  function OstDashboardCtrl($scope, streams, dashboardPath) {
    $scope.dashboard = {
      ost: {},
      usage: {},
      charts: [
        {name: 'iml/read-write-bandwidth/assets/html/read-write-bandwidth.html'},
        {name: 'iml/space-usage/assets/html/space-usage.html'},
        {name: 'iml/file-usage/assets/html/file-usage.html'}
      ]
    };

    $scope.params = {
      id: dashboardPath.getTargetId()
    };

    $scope.fileUsageTitle = 'Object Usage';
    $scope.fileUsageKey = 'Objects Used';

    var targetStream = streams.targetStream('dashboard.ost', $scope);

    targetStream.start({
      id: dashboardPath.getTargetId(),
      jsonMask: 'label,active_host_name,filesystem_name'
    });

    var usageStream = streams.targetStream('dashboard.usage', $scope, 'httpGetMetrics', function transformer (resp) {
      if (!Array.isArray(resp.body) || resp.body.length === 0) {
        resp.body = {};
      } else {
        var data = resp.body[0].data;

        data.filesused = data.filestotal - data.filesfree;
        data.filesData = [
          {key: 'Free', y: data.filesfree},
          {key: 'Used', y: data.filesused}
        ];

        data.bytesfree = data.kbytesfree * 1024;
        data.bytestotal = data.kbytestotal * 1024;
        data.bytesData = [
          {key: 'Free', y: data.bytesfree},
          {key: 'Used', y: data.bytestotal - data.bytesfree}
        ];

        resp.body = data;
      }

      return resp;
    });

    usageStream.start({
      id: dashboardPath.getTargetId(),
      qs: {
        metrics: 'filestotal,filesfree,kbytestotal,kbytesfree',
        latest: true
      }
    });
  }
}());