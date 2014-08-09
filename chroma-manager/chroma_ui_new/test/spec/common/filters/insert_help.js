describe('Insert Help Text Filter', function () {
  'use strict';

  var insertHelp, helpBody, returnVal, result;

  beforeEach(module('filters', function ($provide) {
    returnVal = 'Tested-return-value';
    helpBody = jasmine.createSpy('007').andReturn(returnVal);

    $provide.value('help', {
      get: helpBody
    });
  }));

  beforeEach(inject(function ($filter) {
    insertHelp = $filter('insertHelp');
    result = insertHelp('theKey');
  }));

  it('should use help module for filter', function () {
    expect(helpBody).toHaveBeenCalledOnce();
  });

  it('should return expect help text replacement', function () {
    expect(result).toEqual(returnVal);
  });
});
