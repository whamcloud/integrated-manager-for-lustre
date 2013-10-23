describe('tastypie interceptor', function () {
  'use strict';

  var tastypieInterceptor;

  beforeEach(module('interceptors'));

  beforeEach(inject(function (_tastypieInterceptor_) {
    tastypieInterceptor = _tastypieInterceptor_;
  }));

  it('should move other properties from tastypie response to a new prop', function () {
    var result = tastypieInterceptor.response({
      data: {
        meta: {},
        objects: []
      }
    });

    expect(result).toEqual({
      props: {
        meta: {}
      },
      data: []
    });
  });

  it('should not alter the resp if it doesn\'t look like it originated from tastypie', function () {
    var resp = {
      data: {
        meta: {},
        object: {}
      }
    };

    var result = tastypieInterceptor.response(resp);

    expect(result).toEqual(resp);
  });
});
