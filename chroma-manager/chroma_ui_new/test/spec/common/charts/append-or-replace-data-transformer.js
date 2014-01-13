describe('append or replace data transformer', function () {
  'use strict';

  var appendOrReplaceDataTransformer, stream, deferred, resp, replaceTransformer, appendDataTransformer;

  beforeEach(module('charts'));

  mock.beforeEach(
    function createReplaceTransformerMock() {
      replaceTransformer = jasmine.createSpy('replaceTransformer');

      return {
        name: 'replaceTransformer',
        value: replaceTransformer
      };
    },
    function createAppendDataTransformerMock() {
      appendDataTransformer = jasmine.createSpy('appendDataTransformer');

      return {
        name: 'appendDataTransformer',
        value: appendDataTransformer
      };
    }
  );

  beforeEach(inject(function ($q, _$rootScope_, _appendOrReplaceDataTransformer_) {
    appendOrReplaceDataTransformer = _appendOrReplaceDataTransformer_;

    resp = {
      params: {
        qs: {}
      }
    };

    stream = {};

    deferred = $q.defer();
  }));

  it('should throw if resp.params.qs is not an object', function () {
    expect(shouldThrow).toThrow('resp.params.qs not in expected format for appendOrReplaceDataTransformer!');

    function shouldThrow () {
      resp.params.qs = [];

      appendOrReplaceDataTransformer.call(stream, resp);
    }
  });

  it('should call the replace transformer if unit and size are set', function () {
    resp.params.qs.unit = 'minutes';
    resp.params.qs.size = '25';

    appendOrReplaceDataTransformer(resp, deferred);

    expect(replaceTransformer).toHaveBeenCalledOnceWith(resp, deferred);
  });

  it('should call the append transformer if unit and size are not set', function () {
    appendOrReplaceDataTransformer(resp, deferred);

    expect(appendDataTransformer).toHaveBeenCalledOnceWith(resp, deferred);
  });
});