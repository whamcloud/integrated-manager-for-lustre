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

  angular.module('charts').factory('spliceOldDataTransformer', ['getServerMoment', spliceOldDataTransformerFactory]);

  /**
   * This transformer splices out data older than the current duration.
   */
  function spliceOldDataTransformerFactory (getServerMoment) {
    return function spliceOldDataTransformer (resp) {
      var data = this.getter();
      var errorString = '%s is required for the spliceOldDataTransfomer!';

      if (!Array.isArray(data))
        throw new Error('Data not in expected format for spliceOldDataTransformer!');

      if(this.unit == null)
        throw new Error(errorString.sprintf('Stream.unit'));

      if (this.size == null)
        throw new Error(errorString.sprintf('Stream.size'));

      var start = getServerMoment().subtract(this.unit, this.size).valueOf();

      var deleteSeries = [];

      data.forEach(function (item, index) {
        var deleteCount = 0;

        item.values.some(function (value) {
          if (value.x.valueOf() < start) {
            deleteCount += 1;

            return false;
          }

          return true;
        });

        if (deleteCount > 0)
          item.values.splice(0, deleteCount);

        // If values is empty, mark series for deletion
        if (item.values.length === 0)
          deleteSeries.push(index);
      });

      deleteSeries.forEach(function spliceSeries(index) {
        data.splice(index, 1);
      });

      return resp;
    };
  }
}());
