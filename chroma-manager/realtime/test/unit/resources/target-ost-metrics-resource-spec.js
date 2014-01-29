'use strict';

var Q = require('q'),
  targetOstMetricsResourceFactory = require('../../../resources/target-ost-metrics-resource');

describe('Target ost metrics resource', function () {
  var TargetResource, TargetOstMetricsResource, targetOstMetricsResource;

  beforeEach(function () {
    TargetResource = function () {

    };

    TargetResource.prototype.httpGetMetrics = jasmine.createSpy('targetResource.httpGetMetrics');
    TargetResource.prototype.httpGetList = jasmine.createSpy('targetResource.httpGetList');

    spyOn(TargetResource, 'call');

    TargetOstMetricsResource = targetOstMetricsResourceFactory(TargetResource, Q);
    targetOstMetricsResource = new TargetOstMetricsResource();
  });

  it('should call the TargetResource', function () {
    expect(TargetResource.call).toHaveBeenCalledOnceWith(targetOstMetricsResource);
  });

  describe('getting ost metrics scenarios', function () {
    it('should return a list of metrics with target.name as key', function (done) {
      TargetResource.prototype.httpGetMetrics.andReturn(Q.when({
        body: {
          '1': [{}]
        }
      }));

      TargetResource.prototype.httpGetList.andReturn(Q.when({
        body: {
          objects: [
            { id: '1', name: 'foo' }
          ]
        }
      }));

      targetOstMetricsResource.httpGetOstMetrics({}).then(function (resp) {
        expect(resp.body).toEqual({
          foo: [{ id : '1' }]
        });

        done();
      });
    });

    it('should leave the key if it can\'t find a target match', function (done) {
      TargetResource.prototype.httpGetMetrics.andReturn(Q.when({
        body: {
          '1': [{}]
        }
      }));

      TargetResource.prototype.httpGetList.andReturn(Q.when({
        body: {
          objects: [
            { id: '2', name: 'foo' }
          ]
        }
      }));

      targetOstMetricsResource.httpGetOstMetrics({}).then(function (resp) {
        expect(resp.body).toEqual({
          1: [{id: '1'}]
        });

        done();
      });
    });

    it('should handle any errors', function (done) {
      var err = new Error('boom!');

      TargetResource.prototype.httpGetMetrics.andReturn(Q.fcall(function () {
        throw err;
      }));

      TargetResource.prototype.httpGetList.andReturn(Q.when({
        body: {
          objects: [
            { id: '2', name: 'foo' }
          ]
        }
      }));

      targetOstMetricsResource.httpGetOstMetrics({}).catch(function (error) {
        expect(error).toBe(err);

        done();
      });
    });

    it('should return an empty object if there were no metrics', function (done) {
      TargetResource.prototype.httpGetMetrics.andReturn(Q.when({
        body: {
          '2': []
        }
      }));

      TargetResource.prototype.httpGetList.andReturn(Q.when({
        body: {
          objects: [
            {id: '2', name: 'foo'}
          ]
        }
      }));

      targetOstMetricsResource.httpGetOstMetrics({}).then(function (resp) {
        expect(resp.body).toEqual({});

        done();
      });
    });
  });

  describe('getting ost metrics', function () {
    var params;

    beforeEach(function () {
      params = {};

      targetOstMetricsResource.httpGetOstMetrics(params);
    });

    it('should get the metrics', function () {
      expect(TargetResource.prototype.httpGetMetrics).toHaveBeenCalledOnceWith(params);
    });

    it('should get the target list', function () {
      var listParams = {
        qs: {
          kind: 'OST',
          limit: 0
        }
      };

      expect(TargetResource.prototype.httpGetList).toHaveBeenCalledOnceWith(listParams);
    });
  });
});