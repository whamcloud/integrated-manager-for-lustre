describe('disconnect handler', function () {
  'use strict';

  var disconnectHandler, replay, $modal, $interval, $rootScope;

  beforeEach(module('exception'));

  mock.beforeEach('$modal', 'replay');

  beforeEach(inject(function (_disconnectHandler_, _$modal_, _$interval_, _replay_, _$rootScope_) {
    disconnectHandler = _disconnectHandler_;
    $modal = _$modal_;
    $interval = _$interval_;
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

    it('should open the dialog', function () {
      expect($modal.open).toHaveBeenCalledOnce();
    });

    it('should call replay::go', function () {
      $interval.flush(5001);

      expect(replay.go).toHaveBeenCalled();
    });

    it('should close the dialog if all replays have been processed', function () {
      $interval.flush(5001);

      replay.goDeferred.resolve();
      replay.hasPending = false;

      $rootScope.$digest();

      expect($modal.instances['disconnect-modal'].close).toHaveBeenCalled();
    });

    it('should not close the dialog if there are replays left', function () {
      $interval.flush(5001);

      replay.goDeferred.resolve();
      replay.hasPending = true;

      $rootScope.$digest();

      expect($modal.instances['disconnect-modal'].close).not.toHaveBeenCalled();
    });

    it('should call replay::go again if it has been resolved/rejected', function () {
      $interval.flush(5001);

      replay.goDeferred.resolve();
      replay.hasPending = true;

      $rootScope.$digest();

      $interval.flush(5001);

      $rootScope.$digest();

      expect(replay.go.callCount).toBe(2);
    });

    it('should not call replay::go again if it has not been resolved/rejected', function () {
      $interval.flush(5000);

      $rootScope.$digest();

      $interval.flush(5000);

      $rootScope.$digest();

      expect(replay.go.callCount).toBe(1);
    });
  });
});
