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


angular.module('fileSystem').factory('fileSystemStreamModelTransformer',
  ['FileSystemStreamModel', fileSystemStreamModelTransformerFactory]);

function fileSystemStreamModelTransformerFactory(FileSystemStreamModel) {
  'use strict';

  /**
   * Transforms incoming stream data to FileSystemStreamModel instances.
   * @param {Array|Object|undefined} resp The server response.
   */
  return function transformer(resp) {
    if (!_.isPlainObject(resp.body))
      throw new Error('fileSystemStreamModelTransformer expects resp.body to be an object!');

    var cloned = _.cloneDeep(resp.body);

    if (Array.isArray(cloned.objects)) {
      cloned.objects.length = 0;

      resp.body.objects.forEach(function enhanceItem(item) {
        var fileSystemStreamModel = new FileSystemStreamModel(item);

        cloned.objects.push(fileSystemStreamModel);
      });
    } else {
      cloned = new FileSystemStreamModel(cloned);
    }

    resp.body = cloned;

    return resp;
  };
}
