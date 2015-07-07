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


angular.module('mds').factory('mdsTransformer', ['moment', function mdsTransformerFactory (moment) {
  'use strict';

  /**
   * Transforms incoming stream data to compute cpu and ram usage
   * @param {Object} resp The response.
   */
  return function transformer(resp) {
    var newVal = resp.body;

    if (!Array.isArray(newVal) )
      throw new Error('mdsTransformer expects resp.body to be an array!');

    if (newVal.length === 0)
      return resp;

    var dataPoints = [
      {
        key: 'cpu',
        values: []
      },
      {
        key: 'ram',
        values: []
      }
    ];

    resp.body = newVal.reduce(function (arr, curr) {
      var cpuSum = curr.data.cpu_user + curr.data.cpu_system + curr.data.cpu_iowait,
        cpuPercentage = (curr.data.cpu_total ? (cpuSum / curr.data.cpu_total) : 0.0),
        cpuUsage = {y: cpuPercentage, x: moment(curr.ts).utc().toDate()};

      arr[0].values.push(cpuUsage);

      var usedMemory = curr.data.mem_MemTotal - curr.data.mem_MemFree,
        memoryPercentage = ( usedMemory / curr.data.mem_MemTotal ),
        ramUsage = {y: memoryPercentage, x: moment(curr.ts).utc().toDate()};

      arr[1].values.push(ramUsage);

      return arr;

    }, dataPoints);

    return resp;
  };
}]);
