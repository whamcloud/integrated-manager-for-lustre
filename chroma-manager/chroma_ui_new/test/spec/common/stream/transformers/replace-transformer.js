describe('replace transformer', function () {
  'use strict';

  var replaceTransformer, stream, data, resp, result;

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
    result = replaceTransformer.call(stream, resp);

    expect(result).toBe(data);
  });

  it('should preserve object references', function () {
    var fakeThingy = {};

    resp.body = [fakeThingy];

    replaceTransformer.call(stream, resp);

    expect(data[0]).toBe(fakeThingy);
  });

  it('should update existing Resource objects', function () {
    var fakeThingy = {id: 1, version: 1, attribute: 'foo'};
    var newFakeThingy = {id: 1, version: 2, attribute: 'bar'};

    data = {objects: [fakeThingy]};
    resp.body = {objects: [newFakeThingy]};

    result = replaceTransformer.call(stream, resp);
    expect(result.objects[0]).toBe(fakeThingy);
    expect(result.objects[0].attribute).toEqual('bar');
    expect(result.objects[1]).toBeUndefined();
  });

  it('should not update Resource objects with older data', function () {
    data = {objects: [{id: 1, version: 2, attribute: 'foo'},
                      {id: 2, version: 3, attribute: 'bar'}]};
    resp.body = {objects: [{id: 1, version: 2, attribute: 'baz'},
                           {id: 2, version: 1, attribute: 'qux'}]};

    result = replaceTransformer.call(stream, resp);
    expect(result.objects[0].attribute).toEqual('foo');
    expect(result.objects[1].attribute).toEqual('bar');
  });

  it('should update existing Resource objects with no version', function () {
    var fakeThingy = {id: 1, attribute: 'foo'};
    var newFakeThingy = {id: 1, attribute: 'bar'};

    data = {objects: [fakeThingy]};
    resp.body = {objects: [newFakeThingy]};

    result = replaceTransformer.call(stream, resp);
    expect(result.objects[0]).toBe(fakeThingy);
    expect(result.objects[0].attribute).toEqual('bar');
    expect(result.objects[1]).toBeUndefined();
  });

  it('should preserve API sort order on Resource objects', function () {
    data = {
      objects: [
        {id: 2, attribute: 'bar'},
        {id: 3, attribute: 'baz'},
        {id: 4, attribute: 'qux'}
      ]
    };

    var newList = [
      {id: 1, attribute: 'foo'},
      {id: 2, attribute: 'gronk'},
      {id: 3, attribute: 'baz'},
      {id: 5, attribute: 'quux'}
    ];

    resp.body = {
      objects: newList
    };

    result = replaceTransformer.call(stream, resp);
    expect(result.objects).toEqual(newList);
  });

  it('should just replace non-Resource objects', function () {
    data = ['a', 'b'];
    resp.body = ['c', 'd'];

    result = replaceTransformer.call(stream, resp);
    expect(result).toEqual(['c', 'd']);
  });
});
