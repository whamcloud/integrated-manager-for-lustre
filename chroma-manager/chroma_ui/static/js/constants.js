//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

(function () {
  'use strict';

  angular.module('constants', [])
    .constant('STATES', {
      ERROR: 'ERROR',
      WARN: 'WARNING',
      GOOD: 'GOOD',
      INFO: 'INFO',
      INCOMPLETE: 'INCOMPLETE',
      CANCELED: 'CANCELED',
      COMPLETE: 'COMPLETE'
    })
    .constant('STATIC_URL', window.STATIC_URL);
}());
