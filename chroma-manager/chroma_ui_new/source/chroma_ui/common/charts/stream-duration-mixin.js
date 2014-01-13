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


angular.module('charts').factory('streamDurationMixin', ['d3', function (d3) {
  'use strict';

  return {
    /**
     * Sets a new duration to stream from.
     * @param {String} unit
     * @param {Number} size
     */
    setDuration: function setDuration (unit, size) {
      this.unit = unit;
      this.size = size;

      var params = {
        qs: {
          unit: unit,
          size: size
        }
      };

      this.updateParams(params);
    },
    /**
     * Mutates params for a full refresh or an update.
     * @param {String} method
     * @param {Object} params
     * @param {Function} cb
     */
    beforeStreaming: function beforeStreaming(method, params, cb) {
      var data = this.getter();

      // If we changed the duration or we don't have any data
      if ((params.qs.unit && params.qs.size) || data.length === 0) {
        delete params.qs.update;
        delete params.qs.begin;
        delete params.qs.end;

        params.qs.size = this.size;
        params.qs.unit = this.unit;

        cb(method, _.cloneDeep(params));

        delete params.qs.size;
        delete params.qs.unit;
      } else {
        var extent = d3.extent(data[0].values, function (d) { return d.x; });

        params.qs.update = true;
        params.qs.begin = extent[0].toISOString();
        params.qs.end = extent[1].toISOString();

        cb(method, _.cloneDeep(params));
      }
    }
  };
}]);