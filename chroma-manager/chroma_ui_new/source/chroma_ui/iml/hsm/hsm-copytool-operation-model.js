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
  .factory('HsmCopytoolOperationModel', ['modelFactory',
  function hsmCopytoolOperationModelFactory (modelFactory) {
    'use strict';

    var HsmCopytoolOperationModel = modelFactory({ url: 'copytool_operation' });

    HsmCopytoolOperationModel.prototype.progress = function () {
      var progress = (this.processed_bytes /
                      this.total_bytes) * 100;

      if (!isFinite(progress)) {
        return 0;
      } else {
        return progress;
      }
    };

    HsmCopytoolOperationModel.prototype.throughput = function () {
      var elapsed = (Date.parse(this.updated_at) -
                     Date.parse(this.started_at)) / 1000;

      if (elapsed < 1 || !isFinite(elapsed)) return 0;

      // bytes/sec
      var throughput = this.processed_bytes / elapsed;
      return isFinite(throughput) ? throughput : 0;
    };

    return HsmCopytoolOperationModel;
  }
]);
