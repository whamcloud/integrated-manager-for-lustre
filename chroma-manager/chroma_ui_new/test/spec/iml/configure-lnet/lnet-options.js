describe('lnet options', function () {
  'use strict';

  var LNET_OPTIONS;

  var range = _.range(-1, 10),
    expectedValues = range.map(function (value) {
      if (value === -1)
        return {name: 'Not Lustre Network', value: value};
      else
        return {name: 'Lustre Network %s'.sprintf(value), value: value};
    });

  beforeEach(module('configure-lnet-module'));

  beforeEach(inject(function (_LNET_OPTIONS_) {
    LNET_OPTIONS = _LNET_OPTIONS_;
  }));

  describe('enum', function () {
    expectedValues.forEach(function (expectedValue, index) {
      it('should have a value for %s.'.sprintf(expectedValue.name), function () {
        expect(LNET_OPTIONS[index]).toEqual(expectedValue);
      });
    });
  });
});
