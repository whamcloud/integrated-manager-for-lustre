describe('ost balance stream', function () {
  'use strict';

  var OstBalanceStream, stream, replaceTransformer, ostBalanceTransformer;

  beforeEach(module('ostBalance'));

  mock.beforeEach(
    function createStreamMock() {
      stream = jasmine.createSpy('stream').andCallFake(function () {
        return function streamInstance() {};
      });

      return {
        name: 'stream',
        value: stream
      };
    }
  );

  beforeEach(inject(function (_OstBalanceStream_, _ostBalanceTransformer_, _replaceTransformer_) {
    OstBalanceStream = _OstBalanceStream_;
    ostBalanceTransformer = _ostBalanceTransformer_;
    replaceTransformer = _replaceTransformer_;
  }));

  it('should configure the stream', function () {
    var expectedConfig = {
      params: {
        qs: {
          kind: 'OST',
          metrics: 'kbytestotal,kbytesfree',
          latest: true
        }
      },
      transformers: [ostBalanceTransformer, replaceTransformer]
    };

    expect(stream).toHaveBeenCalledOnceWith('targetostmetrics', 'httpGetOstMetrics', expectedConfig);
  });

  describe('set percentage', function () {
    var instance;

    beforeEach(function () {
      instance = {
        updateParams: jasmine.createSpy('updateParams')
      };

      OstBalanceStream.prototype.setPercentage.call(instance, 50);
    });

    it('should have a method to set percentage', function () {
      expect(instance.percentage).toBe(50);
    });

    it('should update the params', function () {
      expect(instance.updateParams).toHaveBeenCalledOnce();
    });
  });
});