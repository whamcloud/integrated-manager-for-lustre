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


angular.module('charts').factory('streamDurationMixin', ['getServerMoment', 'd3', function (getServerMoment, d3) {
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
      this.updatedDuration = true;
      this.restart();
    },
    /**
     * Mutates params for a full refresh or an update.
     * @param {String} method
     * @param {Object} params
     * @param {Function} cb
     */
    beforeStreaming: function beforeStreaming(method, params, cb) {
      var data = this.getter();

      var usableValues = _(data).pluck('values').find(function (values) {
        return Array.isArray(values) && values.length > 1;
      });

      // If we updated the duration or we don't have usable values
      if (this.updatedDuration || !usableValues) {
        delete params.qs.update;
        this.updatedDuration = false;

        var end = getServerMoment().milliseconds(0);

        params.qs.end = end.toISOString();
        params.qs.begin = end.subtract(this.size, this.unit).toISOString();

        cb(method, params);
      } else {
        var extent = d3.extent(usableValues, function (d) { return d.x; });

        params.qs.update = true;
        params.qs.begin = extent[0].toISOString();
        params.qs.end = extent[1].toISOString();

        cb(method, _.cloneDeep(params));
      }
    }
  };
}]);
