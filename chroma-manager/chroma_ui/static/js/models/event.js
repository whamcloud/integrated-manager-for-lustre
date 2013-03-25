//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

angular.module('models').factory('eventModel', ['baseMessageModel', function (baseMessageModel) {
  'use strict';

  return baseMessageModel({url: '/api/event/:eventId'});
}]);
