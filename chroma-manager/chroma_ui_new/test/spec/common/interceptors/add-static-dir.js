describe('add static dir interceptor', function () {
  'use strict';

  var addStaticDirInterceptor;

  beforeEach(module('interceptors'));

  mock.beforeEach('STATIC_URL');

  beforeEach(inject(function (_addStaticDirInterceptor_) {
    addStaticDirInterceptor = _addStaticDirInterceptor_;
  }));

  it('should remove the / if one is present at the start of the url', function () {
    var result = addStaticDirInterceptor.request({url: '/adir/afile.html'});

    expect(result).toEqual({url: '/static/adir/afile.html'});
  });

  it('should ignore non-html files', function () {
    var config = {url: '/a/b/c'};

    var result = addStaticDirInterceptor.request(config);

    expect(result).toEqual(config);
  });

  it('should ignore ui bootstrap files', function () {
    var config = {url: '/template/modal.html'};

    var result = addStaticDirInterceptor.request(config);

    expect(result).toEqual(config);
  });
});

