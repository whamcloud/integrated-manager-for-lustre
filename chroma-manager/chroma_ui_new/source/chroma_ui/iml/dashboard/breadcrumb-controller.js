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


(function () {
  'use strict';

  angular.module('dashboard')
    .controller('BreadcrumbCtrl',
      ['$scope', 'streams', 'dashboardPath', BreadcrumbCtrl]);

  function BreadcrumbCtrl($scope, streams, dashboardPath) {
    $scope.breadcrumb = {
      fsData: {},
      serverData: {},
      targetData: {},
      path: dashboardPath,
      getItem: function getItem () {
        if (this.path.isFs())
          return this.fsData;

        if (this.path.isServer())
          return this.serverData;
      }
    };

    var streamsGroup = {
      fs: streams.fileSystemStream('breadcrumb.fsData', $scope),
      server: streams.hostStream('breadcrumb.serverData', $scope),
      target: streams.targetStream('breadcrumb.targetData', $scope)
    };

    handleStreams();

    $scope.$on('routeSegmentChange', handleStreams);

    /**
     * Looks at the current path and toggles
     * streams corresponding to that path.
     */
    function handleStreams () {
      if (!dashboardPath.isDashboard()) return;

      Object.keys(streamsGroup).forEach(function toggleStream(streamName) {
        var capitalized = streamName.charAt(0).toUpperCase() + streamName.slice(1);
        var stream = streamsGroup[streamName];

        if (dashboardPath['is' + capitalized]()) {
          var params = {
            id: dashboardPath['get' + capitalized + 'Id'](),
            jsonMask: 'label'
          };

          stream.start(params);
        } else {
          stream.end();
        }
      });
    }
  }
}());
