describe('Mdt dashboard controller', function () {
  'use strict';

  beforeEach(module('dashboard', function ($provide) {
    $provide.value('streams', {
      targetStream: jasmine.createSpy('targetStream').andReturn({
        start: jasmine.createSpy('start')
      })
    });
  }, {
    dashboardPath: {
      getTargetId: function () {
        return 1;
      }
    }
  }));

  var $scope, streams;

  beforeEach(inject(function ($controller, $rootScope, _streams_) {
    $scope = $rootScope.$new();
    streams = _streams_;

    $controller('MdtDashboardCtrl', {
      $scope: $scope
    });
  }));

  it('should contain the expected charts', function () {
    expect($scope.dashboard.charts).toEqual([
      {name: 'iml/mdo/assets/html/mdo.html'},
      {name: 'iml/space-usage/assets/html/space-usage.html'},
      {name: 'iml/file-usage/assets/html/file-usage.html'}
    ]);
  });

  it('should set the target id for child charts', function () {
    expect($scope.params.id).toBe(1);
  });

  it('should setup the targetStream', function () {
    expect(streams.targetStream).toHaveBeenCalledOnceWith('dashboard.mdt', $scope);
  });

  it('should start the targetStream', function () {
    expect(streams.targetStream.plan().start).toHaveBeenCalledOnceWith({
      id: 1,
      jsonMask: 'active_host_name,filesystem_name,label'
    });
  });

  it('should setup the usageStream', function () {
    expect(streams.targetStream)
      .toHaveBeenCalledOnceWith('dashboard.usage', $scope, 'httpGetMetrics', jasmine.any(Function));
  });

  it('should start the usageStream', function () {
    expect(streams.targetStream.plan().start).toHaveBeenCalledOnceWith({
      id: 1,
      qs: {
        metrics: 'filestotal,filesfree,kbytestotal,kbytesfree',
        latest: true
      }
    });
  });
});