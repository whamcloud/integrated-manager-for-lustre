describe('action dropdown module', function () {
  'use strict';

  beforeEach(module('action-dropdown-module', 'dataFixtures'));

  var groupActionsFilter, groupActionsFixtures;

  beforeEach(inject(function ($filter, _groupActionsFixtures_) {
    groupActionsFilter = $filter('groupActions');
    groupActionsFixtures = _groupActionsFixtures_;
  }));

  it('should order groups', function () {
    groupActionsFixtures.forEach(function testItem (item) {
      var result = groupActionsFilter(item.in);

      expect(result).toEqual(item.out);
    });
  });

});
