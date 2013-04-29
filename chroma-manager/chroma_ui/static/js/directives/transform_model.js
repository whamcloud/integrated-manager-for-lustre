//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================


angular.module('directives').directive('transformModel', function factory() {
  'use strict';
  return {
    restrict: 'A',
    require: 'ngModel',
    link: function postLink(scope, el, attrs, controller) {
      var data = scope.$eval(attrs.transformModel);

      if (data.parser) {
        controller.$parsers.push(data.parser);
      }

      if (data.formatter) {
        controller.$formatters.push(data.formatter);
      }
    }
  };
});
