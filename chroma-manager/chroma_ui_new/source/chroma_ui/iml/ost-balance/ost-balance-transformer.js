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


angular.module('ostBalance').factory('ostBalanceTransformer', ['formatBytes', ostBalanceTransformer]);

function ostBalanceTransformer(formatBytes) {
  'use strict';

  /**
   * Transforms incoming stream data to a format nvd3 can use.
   * @param {Array|undefined} newVal The new data.
   */
  return function transformer(resp) {
    var newVal = resp.body;

    if (!_.isPlainObject(newVal))
      throw new Error('ostBalanceTransformer expects resp.body to be an object!');

    /*jshint validthis: true */
    var percentage = this.percentage;

    resp.body = Object.keys(newVal).reduce(function (arr, key) {
      var data = newVal[key][0].data,
        free = (data.kbytesfree / data.kbytestotal),
        used = 1 - free,
        detail = {
          percentFree: asPercentage(free),
          percentUsed: asPercentage(used),
          bytesFree: asFormattedBytes(data.kbytesfree),
          bytesUsed: asFormattedBytes(data.kbytestotal - data.kbytesfree),
          bytesTotal: asFormattedBytes(data.kbytestotal)
        };

      if (percentage && percentage >= Math.round(used * 100)) return arr;

      arr[0].values.push({x: key, y: used, detail: detail});
      arr[1].values.push({x: key, y: free, detail: detail});

      return arr;
    }, [{key: 'Used bytes', values: []}, {key: 'Free bytes', values: []}]);

    return resp;
  };


  /**
   * Given a number outputs a percentage
   * @param {Number} number
   * @returns {string}
   */
  function asPercentage (number) {
    return Math.round(number * 100) + '%';
  }

  /**
   * Given a number outputs a number formatted to 4 places and rounded to a capacity.
   * @param {Number} number
   * @returns {Number}
   */
  function asFormattedBytes (number) {
    return formatBytes(number * 1024, 4);
  }
}

