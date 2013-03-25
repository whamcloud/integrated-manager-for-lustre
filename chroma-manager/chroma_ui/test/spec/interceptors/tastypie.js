//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================


describe('tastypie interceptor', function () {
  'use strict';

  var spy, deferred, newPromise;

  beforeEach(module('interceptors'));

  beforeEach(inject(function ($injector) {
    spy = jasmine.createSpy('spy');

    deferred = $injector.get('$q').defer();

    newPromise = $injector.get('tastypieInterceptor')(deferred.promise);
    newPromise.then(spy);

  }));

  it('should move other properties from tastypie response to a new prop', inject(function ($rootScope) {
    deferred.resolve({
      data: {
        meta: {},
        objects: []
      }
    });
    $rootScope.$apply();

    expect(spy).toHaveBeenCalledWith({
      props: {
        meta: {}
      },
      data: []
    });
  }));

  it('should not alter the resp if it doesn\'t look like it originated from tastypie', inject(function ($rootScope) {
    var resp = {
      data: {
        meta: {},
        object: {}
      }
    };

    deferred.resolve(resp);
    $rootScope.$apply();

    expect(spy).toHaveBeenCalledWith(resp);
  }));
});
