describe('Regenerator module', function () {
  'use strict';

  beforeEach(module('regenerator-module'));

  var regenerator, setup, teardown, getter;

  beforeEach(inject(function (_regenerator_) {
    regenerator = _regenerator_;

    setup = jasmine.createSpy('setup').andReturn('setup');
    teardown = jasmine.createSpy('teardown');
    getter = regenerator(setup, teardown);
  }));

  describe('getting an object from the cache', function () {
    var item;

    describe('item hasn\'t been created in the cache yet', function () {
      beforeEach(function () {
        item = getter('item');
      });

      it('should not call the tear down function', function () {
        expect(teardown).not.toHaveBeenCalled();
      });

      it('should call the setup function', function () {
        expect(setup).toHaveBeenCalledOnce();
      });
    });

    describe('item already in the cache', function () {
      beforeEach(function () {
        _.times(2, _.partial(getter, 'item'));
      });

      it('should call the teardown function once', function () {
        expect(teardown).toHaveBeenCalledOnceWith('setup');
      });

      it('should call setup twice', function () {
        expect(setup).toHaveBeenCalledTwice();
      });
    });
  });

  describe('destroying the objects in the cache', function () {
    beforeEach(function () {
      getter('item');
      getter.destroy();
    });

    it('should call tear down', function () {
      expect(teardown).toHaveBeenCalledOnce();
    });
  });
});
