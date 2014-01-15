describe('stateful resource mixin', function () {
  'use strict';

  var modelFactory, statefulResourceMixin, StatefulResource;

  beforeEach(module('modelFactory'));

  describe('extending a resource', function () {
    beforeEach(inject(function (_modelFactory_, _statefulResourceMixin_) {
      modelFactory = _modelFactory_;
      statefulResourceMixin = _statefulResourceMixin_;

      StatefulResource = modelFactory({ url: 'stateful_thing' });

      _.extend(StatefulResource.prototype, statefulResourceMixin);
    }));

    it('should add its methods to the extended resource', function () {
      for (var method in statefulResourceMixin) {
        expect(StatefulResource.prototype[method])
          .toBe(statefulResourceMixin[method]);
      }
    });
  });

  describe('handling state changes', function () {
    beforeEach(inject(function (_statefulResourceMixin_) {
      statefulResourceMixin = _statefulResourceMixin_;

      statefulResourceMixin.id = 1;

      statefulResourceMixin.constructor = {update: function () {}};
      spyOn(statefulResourceMixin.constructor, 'update').andReturn({
        $promise: null
      });
    }));

    it('testStateChange() should call update() with dry_run: true', function () {
      statefulResourceMixin.testStateChange('fakeState');

      expect(statefulResourceMixin.constructor.update).toHaveBeenCalledWith(
        { id: statefulResourceMixin.id },
        { dry_run: true, state: 'fakeState' },
        undefined, undefined
      );
    });

    it('changeState() should call update() without dry_run', function () {
      statefulResourceMixin.changeState('fakeState');

      expect(statefulResourceMixin.constructor.update).toHaveBeenCalledWith(
        { id: statefulResourceMixin.id },
        { state: 'fakeState' },
        undefined, undefined
      );
    });
  });
});
