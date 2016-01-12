describe('disconnect handler', function () {
  'use strict';

  var disconnectHandler, replay, $dialog, interval, $rootScope;

  beforeEach(module('exception'));

  mock.beforeEach('$dialog', 'replay');

  beforeEach(inject(function (_disconnectHandler_, _$dialog_, _interval_, _replay_, _$rootScope_) {
    disconnectHandler = _disconnectHandler_;
    $dialog = _$dialog_;
    interval = _interval_;
    replay = _replay_;
    $rootScope = _$rootScope_;
  }));

  describe('adding a config', function () {
    var config, addPromise;

    beforeEach(function () {
      config = {method: 'GET', url: '/foo'};
      addPromise = disconnectHandler.add(config);
    });

    it('should add to replay', function () {
      expect(replay.add).toHaveBeenCalledWith(config);
    });

    it('should check if dialog is open', function () {
      expect($dialog.dialog.spy.isOpen).toHaveBeenCalled();
    });

    it('should open the dialog', function () {
      expect($dialog.dialog.spy.open).toHaveBeenCalled();
    });

    it('should call replay::go', function () {
      interval.flush();

      expect(replay.go).toHaveBeenCalled();
    });

    it('should close the dialog if all replays have been processed', function () {
      interval.flush();

      replay.goDeferred.resolve();
      replay.hasPending = false;

      $rootScope.$digest();

      expect($dialog.dialog.spy.close).toHaveBeenCalled();
    });

    it('should not close the dialog if there are replays left', function () {
      interval.flush();

      replay.goDeferred.resolve();
      replay.hasPending = true;

      $rootScope.$digest();

      expect($dialog.dialog.spy.close).not.toHaveBeenCalled();
    });

    it('should call replay::go again if it has been resolved/rejected', function () {
      interval.flush();

      replay.goDeferred.resolve();
      replay.hasPending = true;

      $rootScope.$digest();

      interval.flush();

      $rootScope.$digest();

      expect(replay.go.calls.count()).toBe(2);
    });

    it('should not call replay::go again if it has not been resolved/rejected', function () {
      interval.flush();

      $rootScope.$digest();

      interval.flush();

      $rootScope.$digest();

      expect(replay.go.calls.count()).toBe(1);
    });
  });
});
