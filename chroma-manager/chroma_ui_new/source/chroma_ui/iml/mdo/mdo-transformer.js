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


angular.module('mdo').factory('mdoTransformer', [function mdoTransformerFactory() {
  'use strict';

  /**
   * Transforms incoming stream data to a format nvd3 can use.
   * @param {Object} resp The response.
   */
  return function transformer (resp) {
    var newVal = resp.body;

    if (!Array.isArray(newVal) )
      throw new Error('mdoTransformer expects resp.body to be an array!');

    if (!newVal.length)
      return resp;


    var newData = [
      { key: 'stats_close',    values: [] },
      { key: 'stats_getattr',  values: [] },
      { key: 'stats_getxattr', values: [] },
      { key: 'stats_link',     values: [] },
      { key: 'stats_mkdir',    values: [] },
      { key: 'stats_mknod',    values: [] },
      { key: 'stats_open',     values: [] },
      { key: 'stats_rename',   values: [] },
      { key: 'stats_rmdir',    values: [] },
      { key: 'stats_setattr',  values: [] },
      { key: 'stats_statfs',   values: [] },
      { key: 'stats_unlink',   values: [] }
    ];

    newVal.forEach(function (item) {
      var date = new Date(item.ts);

      _.forEach(item.data, function (val, key) {
        var match = _.where(newData, {key: key.trim()})[0];

        if (!match) throw new Error('No matching item found!');

        match.values.push({x: date, y: val});
      });
    });

    newData.forEach(function (item) {
      item.key = item.key.replace(/^stats_/, '');
    });

    resp.body = newData;

    return resp;
  };
}]);
