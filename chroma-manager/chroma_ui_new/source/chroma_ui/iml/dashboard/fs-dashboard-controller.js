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
    .controller('FsDashboardCtrl', ['$scope', 'FileSystemStreamModel', 'streams', 'dashboardPath', FsDashboardCtrl]);

  /**
   * Dashboard for filesystem
   * @param {Object} $scope
   * @param {FileSystemStreamModel} FileSystemStreamModel
   * @param {Object} streams
   * @param {Object} dashboardPath
   * @constructor
   */
  function FsDashboardCtrl ($scope, FileSystemStreamModel, streams, dashboardPath) {
    $scope.dashboard = {
      fs: new FileSystemStreamModel({}),
      charts: [
        {name: 'iml/read-write-heat-map/assets/html/read-write-heat-map.html'},
        {name: 'iml/ost-balance/assets/html/ost-balance.html'},
        {name: 'iml/mdo/assets/html/mdo.html'},
        {name: 'iml/read-write-bandwidth/assets/html/read-write-bandwidth.html'},
        {name: 'iml/mds/assets/html/mds.html'},
        {name: 'iml/object-storage-servers/assets/html/object-storage-servers.html'}
      ]
    };

    $scope.params = {
      qs: {
        filesystem_id: dashboardPath.getFsId()
      }
    };

    var fsStream = streams.fileSystemStream('dashboard.fs', $scope);

    fsStream.start({
      id: dashboardPath.getFsId(),
      jsonMask: 'label,mgt(primary_server_name),mdts(primary_server_name),osts,bytes_total,bytes_free,\
files_free,files_total,client_count,immutable_state'
    });
  }
}());

