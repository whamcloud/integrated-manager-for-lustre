describe('stateful model factory', function () {
  'use strict';

  var statefulResourceMixin, statefulModelFactory, StatefulResource;

  beforeEach(module('modelFactory'));

  beforeEach(inject(function (_statefulModelFactory_, _statefulResourceMixin_) {
    statefulModelFactory = _statefulModelFactory_;
    statefulResourceMixin = _statefulResourceMixin_;

    StatefulResource = statefulModelFactory({ url: 'item' });
  }));

  it('should create a resource model with stateful methods', function () {
    for (var method in statefulResourceMixin) {
      /* jshint forin:false */
      expect(StatefulResource.prototype[method])
        .toBe(statefulResourceMixin[method]);
    }
  });
});
