describe('Paging service', function () {
  'use strict';

  var meta;

  beforeEach(module('services'));

  beforeEach(function () {
    meta = {
      limit: 10,
      next: '/api/alert/?limit=10&dismissed=false&offset=10',
      offset: 0,
      previous: null,
      total_count: 67329
    };
  });

  it('should return a function', inject(function (paging) {
    expect(paging).toEqual(jasmine.any(Function));
  }));

  it('should return a pager object given a meta object', inject(function (paging) {
    expect(paging(meta)).toEqual(jasmine.any(Object));
  }));

  it('should have a next offset if available', inject(function (paging) {
    expect(paging(meta).next).toEqual(10);

    meta.next = null;
    expect(paging(meta).next).toBeUndefined();
  }));

  it('should have a previous offset if available', inject(function (paging) {
    expect(paging(meta).previous).toBeUndefined();

    meta.previous = '/api/alert/?limit=10&dismissed=false&offset=20';
    expect(paging(meta).previous).toBe(20);
  }));

  it('should have the total number of pages', inject(function (paging) {
    expect(paging(meta).noOfPages).toBe(6733);
  }));

  it('should have the limit', inject(function (paging) {
    expect(paging(meta).limit).toBe(10);
  }));

  it('should have the current page', inject(function (paging) {
    expect(paging(meta).currentPage).toBe(1);

    meta.offset = 600;
    expect(paging(meta).currentPage).toBe(61);

    meta.offset = 67320;
    expect(paging(meta).currentPage).toBe(6733);
  }));

  it('should have a method to get params', inject(function (paging) {
    expect(paging(meta).getParams).toEqual(jasmine.any(Function));
    expect(paging(meta).getParams()).toEqual({limit: 10, offset: 0});
    expect(paging(meta).getParams(11)).toEqual({limit: 10, offset: 100});
  }));

  it('should take limit 0 into account', inject(function (paging) {
    meta.limit = 0;
    expect(paging(meta).noOfPages).toEqual(0);
    expect(paging(meta).currentPage).toEqual(1);
  }));
});
