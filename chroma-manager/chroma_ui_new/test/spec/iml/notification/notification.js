describe('notification', function () {
  'use strict';

  beforeEach(module('notification'));

  describe('notification controller', function () {
    var $scope, NotificationStream;

    beforeEach(inject(function ($controller, $rootScope) {
      $scope = $rootScope.$new();

      NotificationStream = {
        setup: jasmine.createSpy('notificationStream.setup').andReturn({
          startStreaming: jasmine.createSpy('notificationStream.startStreaming')
        })
      };

      $controller('NotificationCtrl', {
        $scope: $scope,
        NotificationStream: NotificationStream
      });
    }));

    it('should setup the stream', function () {
      expect(NotificationStream.setup).toHaveBeenCalledOnceWith('notification.status', $scope);
    });

    it('should start the stream', function () {
      expect(NotificationStream.setup.plan().startStreaming).toHaveBeenCalledOnce();
    });

    it('should expose a count property', function () {
      $scope.notification.status.count = 5;

      expect($scope.notification.count).toBe(5);
    });

    it('should return the limit from count when it is > 99', function () {
      $scope.notification.status.count = 100;

      expect($scope.notification.count).toBe(99);
    });

    it('should expose an aboveLimit property', function () {
      $scope.notification.status.count = 5;

      expect($scope.notification.aboveLimit).toBe(false);
    });

    it('should be above the limit when count > 99', function () {
      $scope.notification.status.count = 300;

      expect($scope.notification.aboveLimit).toBe(true);
    });
  });

  describe('notification stream', function () {
    var NotificationStream, stream;

    mock.beforeEach('stream');

    beforeEach(inject(function (_NotificationStream_, _stream_) {
      NotificationStream = _NotificationStream_;
      stream = _stream_;
    }));

    it('should create a notification stream', function () {
      expect(stream).toHaveBeenCalledOnceWith('notification', 'httpGetHealth', {
        params: {},
        transformers: jasmine.any(Function)
      });
    });

    it('should set the scope', function () {
      var context = {
        setter: jasmine.createSpy('setter')
      };

      var transformer = stream.mostRecentCall.args[2].transformers.bind(context);

      transformer({body: 'foo'});

      expect(context.setter).toHaveBeenCalledOnceWith('foo');
    });
  });
});



