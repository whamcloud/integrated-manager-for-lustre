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


_.mixin({
  /**
   * Truncates the destination array and pushes the source into it.
   * Operates in place.
   * @param {Array} destination
   * @param {Array} source
   * @returns {Array} The destination.
   */
  replace: function (destination, source) {
    if (!Array.isArray(destination) || !Array.isArray(source))
      throw new Error('Both arguments to replace must be arrays!');
    destination.length = 0;
    source.forEach(function (item) {
      destination.push(item);
    });
    return destination;
  },
  /**
   * Takes an object and deletes the keys it holds.
   * @param {Object} obj
   * @returns {Object} Returns the passed in obj.
   */
  clear: function (obj) {
    var keys;
    try {
      keys = Object.keys(obj);
    } catch (error) {
      throw new Error('Object to clear must be an object!');
    }
    keys.forEach(function (key) {
      delete obj[key];
    });
    return obj;
  }
});
