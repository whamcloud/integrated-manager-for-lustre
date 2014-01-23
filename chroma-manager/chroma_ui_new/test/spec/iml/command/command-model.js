describe('command model', function () {
  'use strict';

  var CommandModel;

  beforeEach(module('command', 'modelFactory'));

  beforeEach(inject(function (_CommandModel_) {
    CommandModel = _CommandModel_;
  }));

  describe('instantiating', function () {
    var instance;

    beforeEach(function () {
      instance = new CommandModel({a: 'b'});
    });

    it('should add the value passed into the constructor to the instance', function () {
      expect(instance.a).toBe('b');
    });
  });
});
