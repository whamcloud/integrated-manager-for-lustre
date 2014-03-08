describe('replace transformer', function () {
  'use strict';

  var replaceTransformer, stream, data, resp;

  beforeEach(module('stream'));

  beforeEach(inject(function (_replaceTransformer_) {
    replaceTransformer = _replaceTransformer_;

    data = [];

    resp = {
      body: []
    };

    stream = {
      getter: jasmine.createSpy('getter').andCallFake(function () {
        return data;
      })
    };
  }));

  it('should replace the data with the response.body', function () {
    var fakeRecord = {};

    resp.body = [fakeRecord];

    replaceTransformer.call(stream, resp);

    expect(data).toEqual([fakeRecord]);
  });

  it('should resolve with the data', function () {
    var result = replaceTransformer.call(stream, resp);

    expect(result).toBe(data);
  });

  it('should preserve object identity', function () {
    function FakeThingy () {}

    resp.body = [new FakeThingy()];

    replaceTransformer.call(stream, resp);

    expect(data[0].constructor).toEqual(FakeThingy);
  });
});
