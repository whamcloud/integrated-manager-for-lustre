describe('The authorization service', function () {
  'use strict';

  var authorization, deferred, GROUPS, $rootScope;

  beforeEach(module('auth'));

  mock.factory(function sessionModelSingleton ($q, _$rootScope_) {
    deferred = $q.defer();
    $rootScope = _$rootScope_;

    return {
      $promise: deferred.promise
    };
  });

  mock.beforeEach('sessionModelSingleton');

  beforeEach(inject(function (_authorization_, _GROUPS_) {
    authorization = _authorization_;
    GROUPS = _GROUPS_;
  }));

  it('should have a method telling if read is enabled', function () {
    authorization.readEnabled().then(function (enabled) {
      expect(enabled).toBe(true);
    });

    deferred.resolve({
      read_enabled: true
    });

    $rootScope.$apply();
  });

  it('should tell if superusers are allowed', function () {
    authorization.groupAllowed(GROUPS.SUPERUSERS).then(function (allowed) {
      expect(allowed).toBe(true);
    });

    deferred.resolve({
      user: {
        groups: [{
          name: GROUPS.SUPERUSERS
        }]
      }
    });

    $rootScope.$apply();
  });

  it('should tell if superusers are not allowed', function () {
    authorization.groupAllowed(GROUPS.SUPERUSERS).then(function (allowed) {
      expect(allowed).toBe(false);
    });

    deferred.resolve({
      user: {
        groups: [{
          name: GROUPS.FS_ADMINS
        }]
      }
    });

    $rootScope.$apply();
  });

  it('should allow a superuser when fs admin is checked', function () {
    authorization.groupAllowed(GROUPS.FS_ADMINS).then(function (allowed) {
      expect(allowed).toBe(true);
    });

    deferred.resolve({
      user: {
        groups: [{
          name: GROUPS.SUPERUSERS
        }]
      }
    });

    $rootScope.$apply();
  });

  it('should allow a fs admin when fs user is checked', function () {
    authorization.groupAllowed(GROUPS.FS_USERS).then(function (allowed) {
      expect(allowed).toBe(true);
    });

    deferred.resolve({
      user: {
        groups: [{
          name: GROUPS.FS_ADMINS
        }]
      }
    });

    $rootScope.$apply();
  });

  it('should disallow a fs admin when superuser is checked', function () {
    authorization.groupAllowed(GROUPS.SUPERUSERS).then(function (allowed) {
      expect(allowed).toBe(false);
    });

    deferred.resolve({
      user: {
        groups: [{
          name: GROUPS.FS_ADMINS
        }]
      }
    });

    $rootScope.$apply();
  });

  it('should allow a fs user when fs user is checked', function () {
    authorization.groupAllowed(GROUPS.FS_USERS).then(function (allowed) {
      expect(allowed).toBe(true);
    });

    deferred.resolve({
      user: {
        groups: [{
          name: GROUPS.FS_USERS
        }]
      }
    });

    $rootScope.$apply();
  });
});