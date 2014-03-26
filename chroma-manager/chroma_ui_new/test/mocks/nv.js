angular.module('nvMock', []).factory('nv', function () {
  'use strict';

  var axis = {};

  axis.orient = jasmine.createSpy('orient').andReturn(axis);
  axis.margin = jasmine.createSpy('margin').andReturn(axis);
  axis.tickPadding = jasmine.createSpy('tickPadding').andReturn(axis);
  axis.showMaxMin = jasmine.createSpy('showMaxMin').andReturn(axis);

  return {
    models: {
      axis: jasmine.createSpy('axis').andReturn(axis)
    },
    utils: {
      optionsFunc: jasmine.createSpy('optionsFunc')
    }
  };
});