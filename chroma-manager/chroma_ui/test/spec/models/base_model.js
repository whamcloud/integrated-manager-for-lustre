//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

describe('Base Model', function () {
  'use strict';

  beforeEach(module('models', 'ngResource', 'services', 'interceptors'));

  afterEach(inject(function ($httpBackend) {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  }));

  it('should return a resource', inject(function (baseModel) {
    expect(baseModel).toBeDefined();
    expect(baseModel).toEqual(jasmine.any(Function));
  }));

  it('should have a patch method', inject(function (baseModel) {
    var patchMethod = baseModel({url: '/a/'}).patch;
    expect(patchMethod).toBeDefined();
    expect(patchMethod).toEqual(jasmine.any(Function));
  }));

  it('should throw an error without a url', inject(function (baseModel) {
    expect(baseModel).toThrow();
  }));

  it('should be callable with just a url', inject(function (baseModel, $httpBackend) {
    var config = {url: '/a/b/c/'};

    $httpBackend
      .expectGET(config.url)
      .respond({});

    var model = baseModel(config);

    var res = model.get();

    $httpBackend.flush();

    expect(res).toEqual(jasmine.any(Object));
  }));

  it('should provide a way to patch a value', inject(function (baseModel, $httpBackend) {
    var spy = jasmine.createSpy('patch').andCallFake(function (value) {
      value.foo = 'bar';

      return value;
    });

    var config = {
      url: '/a/b/c/',
      actions: {
        get: {
          patch: spy
        }
      }
    };

    $httpBackend
      .expectGET(config.url)
      .respond({});

    var res = baseModel(config).get();

    $httpBackend.flush();

    expect(spy).toHaveBeenCalledWith(jasmine.any(Object), jasmine.any(Object));
    expect(res.foo).toEqual('bar');
  }));

  it('should provide a way to execute methods on data', inject(function (baseModel, $httpBackend) {
    var spy = jasmine.createSpy('squareFoo').andCallFake(function () {
      return this.foo * 2;
    });

    var config = {
      url: '/a/b/c/',
      methods: {
        squareFoo: spy
      }
    };

    $httpBackend
      .expectGET(config.url)
      .respond({
        foo: 2
      });

    var res = baseModel(config).get();

    $httpBackend.flush();

    expect(res.squareFoo()).toEqual(4);
    expect(spy).toHaveBeenCalled();
  }));

  it('should override query to return paging', inject(function (baseModel, $httpBackend) {
    var config = {url: '/a/b/c/'};

    $httpBackend
      .expectGET(config.url)
      .respond({
          meta: {
            limit: 10,
            next: "/api/alert/?limit=10&dismissed=false&offset=10",
            offset: 0,
            previous: null,
            total_count: 52
          },
          objects: []
      });

    var res = baseModel(config).query();

    $httpBackend.flush();

    expect(res.paging).toEqual(jasmine.any(Object));
  }));
});
