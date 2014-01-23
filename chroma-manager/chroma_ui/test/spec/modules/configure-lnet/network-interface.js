describe('network interface model', function () {
  'use strict';

  var NetworkInterface, networkInterface, Nids;

  beforeEach(module('configureLnet', function ($provide) {
    var Nids = jasmine.createSpy('Nids').andReturn({
      $save: jasmine.createSpy('nids.$save')
    });

    $provide.value('Nids', Nids);
  }));

  mock.beforeEach('baseModel');

  beforeEach(inject(function (_NetworkInterface_, _Nids_) {
    NetworkInterface = _NetworkInterface_;
    Nids = _Nids_;

    networkInterface = new NetworkInterface();
  }));

  describe('updating interfaces', function () {
    beforeEach(function () {
      var networkInterfaces = [
        {nid: 'blah'},
        {nid: 'blaah'}
      ];

      NetworkInterface.updateInterfaces(networkInterfaces);
    });

    it('should create a list of nids ', function () {
      expect(Nids).toHaveBeenCalledWith({objects: ['blah', 'blaah']});
    });

    it('should save the list', function () {
      expect(Nids.plan().$save).toHaveBeenCalled();
    });
  });
});
