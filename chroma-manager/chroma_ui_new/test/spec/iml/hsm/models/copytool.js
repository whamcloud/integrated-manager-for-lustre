describe('hsm copytool model', function () {
  'use strict';

  var HsmCopytoolModel;

  beforeEach(module('hsm', 'modelFactory'));

  beforeEach(inject(function (_HsmCopytoolModel_) {
    HsmCopytoolModel = _HsmCopytoolModel_;
  }));

  describe('instantiating', function () {
    var instance;

    beforeEach(function () {
      instance = new HsmCopytoolModel({a: 'b'});
    });

    it('should add the value passed into the constructor to the instance', function () {
      expect(instance.a).toBe('b');
    });
  });

  describe('computed status', function () {
    var instance;

    it('should show a started and inactive instance as "idle"', function () {
      var data = {
        state: 'started',
        active_operations_count: 0
      };
      instance = new HsmCopytoolModel(data);

      expect(instance.status()).toEqual('idle');
    });

    it('should show a started and busy instance as "working"', function () {
      var data = {
        state: 'started',
        active_operations_count: 1
      };
      instance = new HsmCopytoolModel(data);

      expect(instance.status()).toEqual('working');
    });

    it('should show a stopped instance as "stopped"', function () {
      var data = {
        state: 'stopped'
      };
      instance = new HsmCopytoolModel(data);

      expect(instance.status()).toEqual('stopped');
    });
  });
});
