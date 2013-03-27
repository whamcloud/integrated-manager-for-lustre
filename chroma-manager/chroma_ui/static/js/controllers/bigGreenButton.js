//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

angular.module('controllers').controller('BigGreenButtonCtrl', ['$scope', 'healthModel',
  function ($scope, healthModel) {
    'use strict';

    $scope.$root.$on('health', function (ev, health) {
      $scope.state = health;
    });
  }]
);
