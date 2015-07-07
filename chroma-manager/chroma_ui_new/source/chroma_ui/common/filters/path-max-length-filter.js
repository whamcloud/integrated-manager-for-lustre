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


(function () {
  'use strict';

  /**
   * The purpose of this filter is to cut down the length of pathnames on the HSM
   * tab to prevent breaking of the table
   */
  angular.module('filters').filter('pathMaxLength', ['$cacheFactory', function($cacheFactory) {

    var cache = $cacheFactory('pathMaxLength', {number: 1024});

    function splitUp(path) {
      var components = { leadingSlash: '' };

      if (path.charAt(0) === '/') {
        components.leadingSlash = '/';
        path = path.slice(1);
      }

      components.parts = path.split('/');
      components.filename = components.parts.splice(-1,1);

      return components;
    }

    function reducePath(pathComponents, maxLength) {
      var path;
      var parts = pathComponents.parts;
      var pointer = Math.ceil(parts.length / 2) - (parts.length % 2 === 1 ? 1 : 0) ;

      parts[pointer] = '...';

      while (1) {
        path = '%s%s/%s'.sprintf(
          pathComponents.leadingSlash,
          parts.join('/'),
          pathComponents.filename
        );

        if ( path.length <= maxLength || parts.length === 1 ) {
          break;
        }

        // pointer is also the # of elements BEFORE the pointer
        var rightCount = parts.length - pointer - 1;
        if (pointer > rightCount) {
          pointer -= 1;
          parts.splice(pointer, 1);
        } else {
          parts.splice(pointer + 1,1);
        }
      }
      return path;
    }

    return function(path, maxLength) {

      if (!_.isString(path) || path.length <= maxLength) {
        return path;
      }

      var cacheKey = maxLength + path;
      var cachedPath = cache.get(cacheKey);
      if (!_.isUndefined(cachedPath)) {
        return cachedPath;
      }

      var pathComponents = splitUp(path);

      if (pathComponents.parts.length > 0) {
        path = reducePath(pathComponents, maxLength);
      }

      // catchall if the filename alone puts us over the length limit
      if (path.length > maxLength) {
        path = '...';
      }
      return cache.put(cacheKey, path);

    };
  }]);
}());
