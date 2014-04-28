describe('append or replace data transformer', function () {
  'use strict';

  var appendOrReplaceDataTransformer, resp, replaceTransformer, appendDataTransformer;

  beforeEach(module('charts', {
    replaceTransformer: jasmine.createSpy('replaceTransformer'),
    appendDataTransformer: jasmine.createSpy('appendDataTransformer')
  }));

  beforeEach(inject(function (_appendOrReplaceDataTransformer_, _appendDataTransformer_, _replaceTransformer_) {
    appendOrReplaceDataTransformer = _appendOrReplaceDataTransformer_;
    appendDataTransformer = _appendDataTransformer_;
    replaceTransformer = _replaceTransformer_;

    resp = {
      params: {
        qs: {}
      }
    };
  }));

  it('should throw if resp.params.qs is not an object', function () {
    expect(shouldThrow).toThrow('resp.params.qs not in expected format for appendOrReplaceDataTransformer!');

    function shouldThrow () {
      resp.params.qs = [];

      appendOrReplaceDataTransformer.call({}, resp);
    }
  });

  it('should call the replace transformer if update is falsly', function () {
    appendOrReplaceDataTransformer(resp);

    expect(replaceTransformer).toHaveBeenCalledOnceWith(resp);
  });

  it('should call the append transformer if update is true', function () {
    resp.params.qs.update = true;

    appendOrReplaceDataTransformer(resp);

    expect(appendDataTransformer).toHaveBeenCalledOnceWith(resp);
  });
});