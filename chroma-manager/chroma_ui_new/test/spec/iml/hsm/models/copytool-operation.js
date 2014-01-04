describe('hsm copytoolOperation model', function () {
  'use strict';

  var HsmCopytoolOperationModel;

  beforeEach(module('hsm', 'modelFactory'));

  beforeEach(inject(function (_HsmCopytoolOperationModel_) {
    HsmCopytoolOperationModel = _HsmCopytoolOperationModel_;
  }));

  describe('instantiating', function () {
    var instance;

    beforeEach(function () {
      instance = new HsmCopytoolOperationModel({a: 'b'});
    });

    it('should add the value passed into the constructor to the instance', function () {
      expect(instance.a).toBe('b');
    });
  });

  describe('computed values', function () {
    var instance;

    beforeEach(function () {
      var date = new Date();
      var data = {
        processed_bytes: 12345,
        total_bytes: 67890,
        started_at: date.toISOString(),
        updated_at: new Date(date.getTime() + 10000).toISOString()
      };

      instance = new HsmCopytoolOperationModel(data);
    });

    it('should include "progress"', function () {
      expect(instance.progress()).toEqual(18.18382677861246);
    });

    it('should include "throughput"', function () {
      expect(instance.throughput()).toEqual(1234.5);
    });
  });

  describe('handling bad inputs', function () {
    it('should return 0 when computed progress is NaN', function () {
      var instance = new HsmCopytoolOperationModel({
        processed_bytes: 'quack',
        total_bytes: 100
      });
      expect(instance.progress()).toEqual(0);
    });

    it('should return 0 for throughput when elapsed time is NaN', function () {
      var instance = new HsmCopytoolOperationModel({
      });
      expect(instance.throughput()).toEqual(0);
    });

    it('should return 0 for throughput when elapsed time is < 1 second', function () {
      var date = new Date().toISOString();
      var instance = new HsmCopytoolOperationModel({
        started_at: date,
        updated_at: date
      });
      expect(instance.throughput()).toEqual(0);
    });

    it('should return 0 when computed throughput is NaN', function () {
      var date = new Date();
      var instance = new HsmCopytoolOperationModel({
        started_at: date.toISOString(),
        updated_at: new Date(date.getTime() + 1000).toISOString(),
        processed_bytes: 'quack'
      });
      expect(instance.throughput()).toEqual(0);
    });
  });
});
