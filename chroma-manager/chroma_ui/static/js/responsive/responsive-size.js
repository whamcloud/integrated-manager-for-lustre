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


(function () {
  'use strict';

  angular.module('responsive', [])
    .constant('responsive_SIZES', {
      DESKTOP: 'desktop',
      DESKTOP_SMALL: 'desktop-small',
      TABLET: 'tablet',
      PHONE: 'phone'
    })
    .factory('responsive_getSize', ['$window', '$document', function ($window, $document) {
      return function getSize() {
        var size = $window.getComputedStyle($document[0].body, ':after').getPropertyValue('content');

        //Normalize to no quotes in the size string.
        return size.replace(/"|'/g, '');
      };
    }])
    .factory('responsive_comparator', ['responsive_getSize', 'responsive_SIZES', function (getSize, SIZES) {
      var sizes = [SIZES.PHONE, SIZES.TABLET, SIZES.DESKTOP_SMALL, SIZES.DESKTOP];

      return function comparator(size) {
        var currentSize = sizes.indexOf(getSize());
        size = sizes.indexOf(size);

        return size > currentSize? 1: size < currentSize? -1: 0;
      };
    }]);
}());
