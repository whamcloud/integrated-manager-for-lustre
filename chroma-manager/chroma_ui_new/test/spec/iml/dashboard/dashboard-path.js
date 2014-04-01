describe('dashboard path', function () {
  'use strict';

  beforeEach(module('dashboard', function ($provide) {
    $provide.value('$routeSegment', {
      contains: jasmine.createSpy('contains'),
      $routeParams: {}
    });
  }));

  var $routeSegment, dashboardPath;

  beforeEach(inject(function (_$routeSegment_, _dashboardPath_) {
    $routeSegment = _$routeSegment_;
    dashboardPath = _dashboardPath_;
  }));

  it('should have a base path', function () {
    expect(dashboardPath.basePath).toEqual('dashboard');
  });

  it('should tell if we are on the base dashboard page', function () {
    dashboardPath.isBase();
    expect($routeSegment.contains).toHaveBeenCalledOnceWith('base');
  });

  it('should tell if we are on the dashboard file system page', function () {
    $routeSegment.$routeParams.fsId = 1;
    expect(dashboardPath.isFs()).toBe(true);
  });

  it('should tell if we are on the dashboard server page', function () {
    $routeSegment.$routeParams.serverId = 2;
    expect(dashboardPath.isServer()).toBe(true);
  });

  it('should tell if we are on a type', function () {
    $routeSegment.$routeParams.serverId = 2;
    expect(dashboardPath.isType()).toBe(true);
  });

  it('should tell if we are on the dashboard OST page', function () {
    dashboardPath.isOst();

    expect($routeSegment.contains).toHaveBeenCalledOnceWith('ost');
  });

  it('should tell if we are on the dashboard MDT page', function () {
    dashboardPath.isMdt();

    expect($routeSegment.contains).toHaveBeenCalledOnceWith('mdt');
  });

  it('should tell if we are on a dashboard target page', function () {
    $routeSegment.contains.when('ost').thenReturn(true);

    expect(dashboardPath.isTarget()).toBe(true);
  });

  it('should get the fsId', function () {
    $routeSegment.$routeParams.fsId = 1;
    expect(dashboardPath.getFsId()).toBe(1);
  });

  it('should get the serverId', function () {
    $routeSegment.$routeParams.serverId = 2;
    expect(dashboardPath.getServerId()).toBe(2);
  });

  it('should get the target ost id', function () {
    $routeSegment.contains.when('ost').thenReturn(true);
    $routeSegment.$routeParams.ostId = 1;
    expect(dashboardPath.getTargetId()).toBe(1);
  });

  it('should get the target mdt id', function () {
    $routeSegment.contains.when('mdt').thenReturn(true);
    $routeSegment.$routeParams.mdtId = 2;
    expect(dashboardPath.getTargetId()).toBe(2);
  });

  it('should get the target ost name', function () {
    $routeSegment.contains.when('ost').thenReturn(true);
    expect(dashboardPath.getTargetName()).toBe('ost');
  });

  it('should get the target mdt name', function () {
    $routeSegment.contains.when('mdt').thenReturn(true);
    expect(dashboardPath.getTargetName()).toBe('mdt');
  });

  it('should get the fs type id', function () {
    $routeSegment.$routeParams.fsId = 1;
    expect(dashboardPath.getTypeId()).toBe(1);
  });

  it('should get the server type id', function () {
    $routeSegment.$routeParams.serverId = 2;
    expect(dashboardPath.getTypeId()).toBe(2);
  });

  it('should get the fs type name', function () {
    $routeSegment.$routeParams.fsId = 1;
    expect(dashboardPath.getTypeName()).toBe('fs');
  });

  it('should get the server type name', function () {
    $routeSegment.$routeParams.serverId = 2;
    expect(dashboardPath.getTypeName()).toBe('server');
  });

  it('should get the fs type label', function () {
    $routeSegment.$routeParams.fsId = 1;
    expect(dashboardPath.getTypeLabel()).toBe('file system');
  });

  it('should get the server type label', function () {
    $routeSegment.$routeParams.serverId = 2;
    expect(dashboardPath.getTypeLabel()).toBe('server');
  });

  it('should get the current fs type path', function () {
    $routeSegment.$routeParams.fsId = 1;
    expect(dashboardPath.getTypePath()).toBe('dashboard/fs/1/');
  });

  it('should get the current server type path', function () {
    $routeSegment.$routeParams.serverId = 2;
    expect(dashboardPath.getTypePath()).toBe('dashboard/server/2/');
  });

  it('should provide the fs ost path', function () {
    $routeSegment.$routeParams.fsId = 1;
    $routeSegment.$routeParams.ostId = 2;
    $routeSegment.contains.when('ost').thenReturn(true);

    expect(dashboardPath.buildPath()).toBe('dashboard/fs/1/ost/2/');
  });

  it('should provide the server mdt path', function () {
    $routeSegment.$routeParams.serverId = 3;
    $routeSegment.$routeParams.mdtId = 4;
    $routeSegment.contains.when('mdt').thenReturn(true);

    expect(dashboardPath.buildPath()).toBe('dashboard/server/3/mdt/4/');
  });

  it('should build the type path from params', function () {
    var params = {
      type: {
        name: 'fs',
        id: 1
      }
    };

    expect(dashboardPath.buildPath(params)).toBe('dashboard/fs/1/');
  });

  it('should build the target path from params', function () {
    var params = {
      type: {
        name: 'server',
        id: 2
      },
      target: {
        name: 'mdt',
        id: 3
      }
    };

    expect(dashboardPath.buildPath(params)).toBe('dashboard/server/2/mdt/3/');
  });
});