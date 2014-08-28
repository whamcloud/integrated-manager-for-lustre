describe('Command monitor controller', function () {
  'use strict';

  beforeEach(module('command'));

  var $scope, commandMonitor, openCommandModal;

  beforeEach(inject(function ($rootScope, $controller) {
    $scope = $rootScope.$new();

    spyOn($scope, '$on').andCallThrough();

    commandMonitor = {
      end: jasmine.createSpy('end'),
      onValue: jasmine.createSpy('onValue')
    };

    openCommandModal = jasmine.createSpy('openCommandModal');

    $controller('CommandMonitorCtrl', {
      $scope: $scope,
      commandMonitor: commandMonitor,
      openCommandModal: openCommandModal
    });
  }));

  describe('destroy', function () {
    it('should listen', function () {
      expect($scope.$on).toHaveBeenCalledOnceWith('$destroy', jasmine.any(Function));
    });

    it('should end the monitor on destroy', function () {
      var handler = $scope.$on.mostRecentCall.args[1];

      handler();

      expect(commandMonitor.end).toHaveBeenCalledOnce();
    });
  });

  describe('on pipeline', function () {
    var handler;

    beforeEach(function () {
      handler = commandMonitor.onValue.mostRecentCall.args[1];

      handler({
        body: {
          objects: [{}]
        }
      });
    });

    it('should listen', function () {
      expect(commandMonitor.onValue).toHaveBeenCalledOnceWith('pipeline', jasmine.any(Function));
    });

    it('should update pending length', function () {
      expect($scope.commandMonitor.pending).toEqual(1);
    });

    it('should save the last response', function () {
      expect($scope.commandMonitor.lastResponse).toEqual({
        body: {
          objects: [{}]
        }
      });
    });

    it('should open the command modal with the last response', function () {
      $scope.commandMonitor.showPending();

      expect(openCommandModal).toHaveBeenCalledOnceWith({
        body: {
          objects: [{}]
        }
      });
    });
  });
});

describe('Command monitor', function () {
  'use strict';

  var requestSocket;

  beforeEach(module('command', function ($provide) {
    requestSocket = jasmine.createSpy('requestSocket').andReturn({
      sendGet: jasmine.createSpy('sendGet'),
      addPipe: jasmine.createSpy('addPipe')
    });

    $provide.value('requestSocket', requestSocket);
  }));

  var commandMonitor;

  beforeEach(inject(function (_commandMonitor_) {
    commandMonitor = _commandMonitor_;
  }));

  it('should create a spark', function () {
    expect(requestSocket).toHaveBeenCalledOnce();
  });

  it('should return a spark', function () {
    expect(commandMonitor).toEqual(requestSocket.plan());
  });

  it('should get pending commands', function () {
    expect(commandMonitor.sendGet).toHaveBeenCalledOnceWith('/command', {
      qs: {
        limit: 0,
        errored: false,
        complete: false
      }
    });
  });

  it('should create a pipeline', function () {
    expect(commandMonitor.addPipe).toHaveBeenCalledOnceWith(jasmine.any(Function));
  });

  it('should filter cancelled commands', function () {
    var pipe = commandMonitor.addPipe.mostRecentCall.args[0];

    var response = pipe({
      body: {
        objects: [
          { cancelled: true },
          { cancelled: false }
        ]
      }
    });

    expect(response).toEqual({
      body: {
        objects: [
          { cancelled: false }
        ]
      }
    });
  });
});
