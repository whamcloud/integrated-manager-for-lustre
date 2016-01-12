mock.register('replay', function ($q) {
  'use strict';

  var replay = {
    hasPending: true,
    isIdempotent: jasmine.createSpy('isIdempotent').and.callFake(this.isIdempotent || function () {
      return true;
    }),
    add: jasmine.createSpy('add').and.callFake(this.add || function () {
      return $q.defer().promise;
    }),
    go: jasmine.createSpy('go').and.callFake(this.go || function () {
      replay.goDeferred = $q.defer();

      return replay.goDeferred.promise;
    })
  };

  return replay;
});
