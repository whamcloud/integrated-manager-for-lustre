describe('Insert help text filter', function () {
  'use strict';

  var insertHelp, help, result;

  beforeEach(module('filters', function ($provide) {
    help = {
      get: jasmine.createSpy('helpBody').andReturn({
        valueOf: jasmine.createSpy('valueOf')
      })
    };

    $provide.value('help', help);
  }));

  beforeEach(inject(function ($filter) {
    insertHelp = $filter('insertHelp');
  }));

  describe('without params', function () {
    beforeEach(function () {
      result = insertHelp('key');
    });

    it('should retrieve values from help', function () {
      expect(help.get).toHaveBeenCalledOnce();
    });

    it('should return the wrapper', function () {
      expect(result).toEqual(help.get.plan());
    });
  });

  describe('with params', function () {
    beforeEach(function () {
      help.get.plan()
        .valueOf.andReturn('This row has changed locally. Click to reset value to %(remote)s');

      result = insertHelp('key', {
        remote: 'Lustre Network 0'
      });
    });

    it('should populate the help text with params', function () {
      expect(result.valueOf())
        .toEqual('This row has changed locally. Click to reset value to Lustre Network 0');
    });
  });
});
