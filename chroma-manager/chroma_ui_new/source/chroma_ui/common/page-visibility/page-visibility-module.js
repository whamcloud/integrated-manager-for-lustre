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

  angular.module('pageVisibility', []).service('pageVisibility', ['$document', PageVisibility]);

  /**
   * Abstracts browser differences in the page visibility api.
   * @param {Object} $document
   * @constructor
   */
  function PageVisibility($document) {
    var hidden, visibilityChange;

    var BASE_VISIBILITY_NAME = 'visibilitychange';
    var document = $document[0];

    if (document.hidden != null) {
      hidden = 'hidden';
      visibilityChange = BASE_VISIBILITY_NAME;
    } else if (document.mozHidden != null) {
      hidden = 'mozHidden';
      visibilityChange = 'moz' + BASE_VISIBILITY_NAME;
    } else if (document.msHidden != null) {
      hidden = 'msHidden';
      visibilityChange = 'ms' + BASE_VISIBILITY_NAME;
    } else if (document.webkitHidden != null) {
      hidden = 'webkitHidden';
      visibilityChange = 'webkit' + BASE_VISIBILITY_NAME;
    }

    /**
     * Registers a listener to fire when page visibility changes.
     * @param {Function} func
     * @returns {Function} A deregistration function to remove the listener.
     */
    this.onChange = function onChange(func) {
      document.addEventListener(visibilityChange, onVisibilityChange);

      return function deregister() {
        document.removeEventListener(visibilityChange, onVisibilityChange);
      };

      function onVisibilityChange() {
        func(document[hidden]);
      }
    };
  }
}());
