describe('Server dashboard controller', function () {
  'use strict';

  beforeEach(module('dashboard', function ($provide) {
    $provide.value('streams', {
      hostStream: jasmine.createSpy('hostStream').andReturn({
        start: jasmine.createSpy('start')
      })
    });
  }, {
    dashboardPath: {
      getServerId: function () {
        return 1;
      }
    }
  }));

  var $scope, streams;

  beforeEach(inject(function ($controller, $rootScope, _streams_) {
    $scope = $rootScope.$new();
    streams = _streams_;

    $controller('ServerDashboardCtrl', {
      $scope: $scope
    });
  }));

  it('should contain the expected charts', function () {
    expect($scope.dashboard.charts).toEqual([
      {name: 'iml/read-write-bandwidth/assets/html/read-write-bandwidth.html'},
      {name: 'iml/cpu-usage/assets/html/cpu-usage.html'},
      {name: 'iml/memory-usage/assets/html/memory-usage.html'}
    ]);
  });

  it('should pass the host id to child charts', function () {
    expect($scope.params.id).toBe(1);
  });

  it('should pass the host id to the readWriteBandwidth chart', function () {
    expect($scope.readWriteBandwidthParams.qs.host_id).toBe(1);
  });

  it('should setup the hostStream', function () {
    expect(streams.hostStream).toHaveBeenCalledOnceWith('dashboard.server', $scope);
  });

  it('should start the hostStream', function () {
    expect(streams.hostStream.plan().start).toHaveBeenCalledOnceWith({
      id: 1,
      jsonMask: 'label'
    });
  });
});