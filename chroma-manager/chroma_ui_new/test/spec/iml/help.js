describe('Help', function () {
  'use strict';

  var help;

  beforeEach(module('help', function ($provide) {
    $provide.constant('HELP_TEXT', {
      foo: 'bar'
    });
  }));


  beforeEach(inject(function (_help_) {
    help = _help_;
  }));

  it('should provide the sce value', function () {
    expect(help.get('foo').valueOf()).toBe('bar');
  });

  it('should provide the same instance if called twice', function () {
    expect(help.get('foo')).toBe(help.get('foo'));
  });

  it('should throw if a non-existent key is fetched', function () {
    expect(help.get.bind(null, 'not a real value')).toThrow();
  });
});
