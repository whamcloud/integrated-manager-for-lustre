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


angular.module('readWriteHeatMap').factory('readWriteHeatMapTransformer', [readWriteHeatMapTransformerFactory]);

function readWriteHeatMapTransformerFactory() {
  'use strict';

  /**
   * Transforms incoming protocol data to display write as a negative value.
   * @param {Object} resp The response.
   * @param {Object} deferred The deferred to pipe through.
   */
  return function transformer(resp, deferred) {
    var newVal = resp.body;

    if (!_.isPlainObject(newVal))
      throw new Error('readWriteHeatMapTransformer expects resp.body to be an object!');

    /*jshint validthis: true */
    var type = this.type;

    resp.body = Object.keys(newVal).reduce(function (arr, key) {
      var ost = {key: key, values: []};

      newVal[key].forEach(function (item) {
        ost.values.push({
          x: new Date(item.ts),
          z: item.data[type]
        });
      });

      arr.push(ost);

      return arr;
    }, []);

    deferred.resolve(resp);
  };
}

