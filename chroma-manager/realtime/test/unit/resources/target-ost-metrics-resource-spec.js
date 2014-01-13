'use strict';

var sinon = require('sinon'),
  targetOstMetricsResourceFactory = require('../../../resources/target-ost-metrics-resource');

require('jasmine-sinon');

describe('Target ost metrics resource', function () {
  var TargetResource, TargetOstMetricsResource, targetOstMetricsResource;

  beforeEach(function () {
    TargetResource = function () {

    };

    TargetResource.prototype.httpGetMetrics = sinon.spy();
    TargetResource.prototype.httpGetList = sinon.spy();

    sinon.stub(TargetResource, 'call');


    TargetOstMetricsResource = targetOstMetricsResourceFactory(TargetResource);
    targetOstMetricsResource = new TargetOstMetricsResource();
  });

  it('should call the TargetResource', function () {
    expect(TargetResource.call).toHaveBeenCalledWithExactly(targetOstMetricsResource);
  });

  describe('getting ost metrics scenarios', function () {
    it('should return a list of metrics with target.name as key', function (done) {
      targetOstMetricsResource.httpGetOstMetrics({}, cb);

      TargetResource.prototype.httpGetMetrics.callArgWith(1, null, [
        { fakeRespProp: 'fakeRespValue' },
        { '1': {fakeMetricsProp: 'fakeMetricsValue'} }
      ]);

      TargetResource.prototype.httpGetList.callArgWith(1, null, [
        { fakeRespProp: 'fakeRespValue' },
        {
          objects: [
            {id: '1', name: 'foo'}
          ]
        }
      ]);

      function cb () {
        expect(arguments).toEqual([
          null,
          { fakeRespProp : 'fakeRespValue' },
          {
            foo : { fakeMetricsProp : 'fakeMetricsValue' }
          },
          {}
        ]);

        done();
      }
    });

    it('should leave the key if it can\'t find a target match', function (done) {
      targetOstMetricsResource.httpGetOstMetrics({}, cb);

      TargetResource.prototype.httpGetMetrics.callArgWith(1, null, [
        { fakeRespProp: 'fakeRespValue' },
        { '1': {fakeMetricsProp: 'fakeMetricsValue'} }
      ]);

      TargetResource.prototype.httpGetList.callArgWith(1, null, [
        { fakeRespProp: 'fakeRespValue' },
        {
          objects: [
            {id: '2', name: 'foo'}
          ]
        }
      ]);

      function cb () {
        expect(arguments).toEqual([
          null,
          { fakeRespProp : 'fakeRespValue' },
          {
            1: { fakeMetricsProp : 'fakeMetricsValue' }
          },
          {}
        ]);

        done();
      }
    });

    it('should handle any errors', function (done) {
      var err = new Error('boom!');

      targetOstMetricsResource.httpGetOstMetrics({}, cb);

      TargetResource.prototype.httpGetMetrics.callArgWith(1, err);

      TargetResource.prototype.httpGetList.callArgWith(1, null, {});

      function cb () {
        expect(arguments).toEqual([err]);

        done();
      }
    });
  });

  describe('getting ost metrics', function () {
    var params, cb;

    beforeEach(function () {
      params = {};
      cb = sinon.spy();

      targetOstMetricsResource.httpGetOstMetrics(params, cb);
    });

    it('should get the metrics', function () {
      expect(TargetResource.prototype.httpGetMetrics).toHaveBeenAlwaysCalledWithExactly(params, sinon.match.func);
    });

    it('should get the target list', function () {
      var listParams = {
        qs: {
          kind: 'OST',
          limit: 0
        }
      };

      expect(TargetResource.prototype.httpGetList).toHaveBeenAlwaysCalledWithExactly(listParams, sinon.match.func);
    });
  });
});