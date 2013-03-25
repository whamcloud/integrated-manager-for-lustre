//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

/**
 * A Factory for accessing alerts.
 */
angular.module('models').factory('alertModel', function ($resource, baseMessageModel) {
  'use strict';

  return baseMessageModel({url: '/api/alert/:alertId'});
});

