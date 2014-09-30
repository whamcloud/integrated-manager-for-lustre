describe('hostlist filter service', function () {
  'use strict';

  var pdshFilter, naturalSortFilter;

  beforeEach(module('server', function ($provide) {
    pdshFilter = jasmine.createSpy('pdshFilter');
    $provide.value('pdshFilter', pdshFilter);

    naturalSortFilter = jasmine.createSpy('naturalSortFilter');
    $provide.value('naturalSortFilter', naturalSortFilter);
  }));

  var hostlistFilter;

  beforeEach(inject(function (_hostlistFilter_) {
    hostlistFilter = _hostlistFilter_;
  }));

  it('should expose the expected interface', function () {
    expect(hostlistFilter).toEqual({
      setHosts: jasmine.any(Function),
      setHash: jasmine.any(Function),
      setFuzzy: jasmine.any(Function),
      setReverse: jasmine.any(Function),
      compute: jasmine.any(Function)
    });
  });

  describe('computing a filtered hostlist', function () {
    beforeEach(function () {
      pdshFilter.andReturn('host1Filtered');

      hostlistFilter
        .setHosts(['host1', 'host2'])
        .setHash({host1: ''})
        .setFuzzy(true)
        .setReverse(false)
        .compute();
    });

    it('should call the pdsh filter', function () {
      expect(pdshFilter).toHaveBeenCalledOnceWith(['host1', 'host2'], {host1: ''}, jasmine.any(Function), true);
    });

    it('should call the natural sort filter', function () {
      expect(naturalSortFilter).toHaveBeenCalledOnceWith('host1Filtered', jasmine.any(Function), false);
    });
  });
});
