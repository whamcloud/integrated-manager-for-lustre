describe('Confirm server action modal', function () {
  'use strict';

  beforeEach(module('server'));

  var $scope, $modalInstance, hosts, action, requestSocket, confirmServer;

  beforeEach(inject(function ($rootScope, $controller) {
    $scope = $rootScope.$new();

    $modalInstance = {
      close: jasmine.createSpy('close'),
      dismiss: jasmine.createSpy('dismiss')
    };

    hosts = [{}];

    action = {
      value: 'Install Updates',
      message: 'Installing updates',
      convertToJob: jasmine.createSpy('convertToJob').andReturn({
        class_name: 'foo',
        args: {
          host_id: '1'
        }
      })
    };

    requestSocket = jasmine.createSpy('requestSocket').andReturn({
      sendPost: jasmine.createSpy('sendPost'),
      end: jasmine.createSpy('end')
    });

    $controller('ConfirmServerActionModalCtrl', {
      $scope: $scope,
      $modalInstance: $modalInstance,
      hosts: hosts,
      action: action,
      requestSocket: requestSocket
    });

    confirmServer = $scope.confirmServerActionModal;
  }));

  it('should set hosts on the scope', function () {
    expect(confirmServer.hosts).toBe(hosts);
  });

  it('should set the actionName on the scope', function () {
    expect(confirmServer.actionName).toEqual(action.value);
  });

  it('should set inProgress on the scope', function () {
    expect(confirmServer.inProgress).toBe(false);
  });

  it('should dismiss the modal on cancel', function () {
    confirmServer.cancel();

    expect($modalInstance.dismiss).toHaveBeenCalledOnceWith('cancel');
  });

  describe('go', function () {
    var spark;

    beforeEach(function () {
      confirmServer.go();

      spark = requestSocket.plan();
    });

    it('should set inProgress to true', function () {
      expect(confirmServer.inProgress).toBe(true);
    });

    it('should create a spark', function () {
      expect(requestSocket).toHaveBeenCalledOnce();
    });

    it('should post a command', function () {
      expect(spark.sendPost).toHaveBeenCalledOnceWith('/command', {
        json: {
          message: action.message,
          jobs: action.convertToJob.plan()
        }
      }, jasmine.any(Function));
    });

    describe('acking the post', function () {
      var ack;

      beforeEach(function () {
        ack = spark.sendPost.mostRecentCall.args[2];
      });

      it('should end the spark', function () {
        ack({body: []});

        expect(spark.end).toHaveBeenCalledOnce();
      });

      it('should throw if error', function () {
        expect(shouldThrow).toThrow();

        function shouldThrow () {
          ack({error: {}});
        }
      });

      it('should close the modal with data', function () {
        ack({body: []});

        expect($modalInstance.close).toHaveBeenCalledOnceWith([]);
      });

      it('should close the modal without data', function () {
        confirmServer.go(true);
        requestSocket.plan().sendPost.mostRecentCall.args[2]({body: []});

        expect($modalInstance.close).toHaveBeenCalledOnceWith(undefined);
      });
    });
  });
});
