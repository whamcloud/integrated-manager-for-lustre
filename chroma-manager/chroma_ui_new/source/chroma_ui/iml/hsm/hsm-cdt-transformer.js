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


angular.module('hsm')
  .factory('hsmCdtTransformer', [function hsmCdtTransformerFactory() {
    'use strict';

    /**
     * Transforms incoming stream data to compute HSM stats
     * @param {Array|undefined} newVal The new data.
     */
    return function transformer(resp) {
      if (!Array.isArray(resp.body) )
        throw new Error('Transformer expects resp.body to be an array!');

      if (resp.body.length === 0)
        return resp;

      var dataPoints = [
        {
          key: 'waiting requests',
          values: []
        },
        {
          key: 'running actions',
          values: []
        },
        {
          key: 'idle workers',
          values: []
        }
      ];

      resp.body = resp.body.reduce(function (arr, curr) {
        var waiting = Math.round(curr.data.hsm_actions_waiting);
        var running = Math.round(curr.data.hsm_actions_running);
        var idle = Math.round(curr.data.hsm_agents_idle);
        var now = new Date(curr.ts);

        arr[0].values.push({
          y: waiting,
          x: now
        });
        arr[1].values.push({
          y: running,
          x: now
        });
        arr[2].values.push({
          y: idle,
          x: now
        });

        return arr;

      }, dataPoints);

      return resp;
    };
  }
]);
