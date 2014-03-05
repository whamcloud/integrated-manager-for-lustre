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

angular.module('readWriteHeatMap').constant('readWriteHeatMapTypes', {
  READ: 'stats_read_bytes',
  WRITE: 'stats_write_bytes'
});

angular.module('readWriteHeatMap').factory('ReadWriteHeatMapStream', ['stream', 'readWriteHeatMapTransformer',
  'replaceTransformer', 'readWriteHeatMapTypes', readWriteHeatMapFactory]);

function readWriteHeatMapFactory(stream, readWriteHeatMapTransformer,
                                 replaceTransformer, readWriteHeatMapTypes) {
  'use strict';

  var ReadWriteHeatMapStream = stream('targetostmetrics', 'httpGetOstMetrics', {
    params: {
      qs: {
        kind: 'OST',
        metrics: 'stats_read_bytes,stats_write_bytes',
        num_points: '20'
      }
    },
    transformers: [readWriteHeatMapTransformer, replaceTransformer]
  });

  Object.defineProperty(ReadWriteHeatMapStream.prototype, 'type', {
    set: function (value) {
      if (value in _.invert(readWriteHeatMapTypes)) {
        this._value = value;
      } else {
        throw new Error('Type: %s is not a valid type!'.sprintf(value));
      }
    },
    get: function () {
      return this._value;
    }
  });

  /**
   * Switches the type, which triggers a watch to fire.
   * @param {String} type
   */
  ReadWriteHeatMapStream.prototype.switchType = function switchType(type) {
    this.type = type;

    this.getter().map(function getValues(item) {
      return item.values;
    })
    .forEach(function switchItemType(values) {
      values.forEach(function (item) {
        item.z = item[this.type];
      }, this);
    }, this);
  };

  ReadWriteHeatMapStream.TYPES = readWriteHeatMapTypes;

  return ReadWriteHeatMapStream;
}
