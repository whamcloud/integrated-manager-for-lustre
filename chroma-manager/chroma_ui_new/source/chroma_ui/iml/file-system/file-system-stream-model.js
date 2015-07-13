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


angular.module('fileSystem').factory('FileSystemStreamModel', ['formatBytes', 'd3', function (formatBytes, d3) {
  'use strict';

  var siFormatter = d3.format('s');

  /**
   * Enhances file system data with model methods.
   * @param value
   * @constructor
   */
  function FileSystemStreamModel (value) {
    angular.copy(value || {}, this);

    this.spaceGraphData = [
      {
        key: 'Free',
        y: this.bytes_free
      },
      {
        key: 'Used',
        y: this.bytes_total - this.bytes_free
      }
    ];

    this.usageGraphData = [
      {
        key: 'Free',
        y: this.files_free
      },
      {
        key: 'Used',
        y: this.files_total - this.files_free
      }
    ];
  }

  FileSystemStreamModel.prototype.STATES = Object.freeze({
    MONITORED: 'monitored',
    MANAGED: 'managed'
  });

  FileSystemStreamModel.prototype.getState = function getState() {
    return (this.immutable_state ? this.STATES.MONITORED : this.STATES.MANAGED);
  };

  FileSystemStreamModel.prototype.getUsedSpace = function getUsedSpace () {
    return formatBytes(this.bytes_total - this.bytes_free);
  };

  FileSystemStreamModel.prototype.getTotalSpace = function getTotalSpace () {
    return formatBytes(this.bytes_total);
  };

  FileSystemStreamModel.prototype.getUsedFiles = function getUsedFiles () {
    return siFormatter(this.files_total - this.files_free);
  };

  FileSystemStreamModel.prototype.getTotalFiles = function getTotalFiles () {
    return siFormatter(this.files_total);
  };

  return FileSystemStreamModel;
}]);
