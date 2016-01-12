describe('Health model', function () {
  'use strict';

  var $httpBackend;
  var healthSpy;
  var WARN;
  var ERROR;
  var GOOD;
  var healthModel;
  var interval;

  var urls = {
    alert: '/api/alert/?active=true&limit=0&severity__in=WARNING&severity__in=ERROR'
  };

  /**
   * Sets up $httpBackend responses for the passed in config object.
   * @param {object} [config]
   */
  function expectReqRes(config) {
    config = config || {};

    Object.keys(urls).forEach(function (url) {
      $httpBackend
        .expectGET(urls[url])
        .respond({meta: {}, objects: config[url] || []});
    });
  }

  beforeEach(module('constants', 'models', 'ngResource', 'services', 'interceptors', function ($provide) {
    // Mock out this dep.
    $provide.value('paging', jasmine.createSpy('paging'));
  }));

  beforeEach(inject(function (_$httpBackend_, _STATES_, _healthModel_, _interval_, $rootScope) {
    $httpBackend = _$httpBackend_;
    WARN = _STATES_.WARN;
    ERROR = _STATES_.ERROR;
    GOOD = _STATES_.GOOD;

    interval = _interval_;
    healthSpy = jasmine.createSpy('health');
    var scope = $rootScope.$new();
    scope.$on('health', healthSpy);

    healthModel = _healthModel_;
  }));

  afterEach(function () {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  });

  describe('working with health', function () {
    it('should broadcast a health event as a listening mechanism', function () {
      expectReqRes();
      healthModel();
      $httpBackend.flush();
      expect(healthSpy).toHaveBeenCalledWith(jasmine.any(Object), { health: GOOD, count: 0 });
    });

    it('should it should emit a health event after calling', function () {
      expectReqRes();
      healthModel();
      $httpBackend.flush();
      expect(healthSpy.calls.count()).toBe(1);
    });

    it('should emit a health event after each interval', function () {
      expectReqRes();
      healthModel();
      $httpBackend.flush();

      expectReqRes();
      interval.flush();
      $httpBackend.flush();

      expect(healthSpy.calls.count()).toBe(2);
    });

    it('should be in error when 1 or more error alerts are active', function () {
      expectReqRes({
        alert: [
          {
            severity: ERROR
          },
          {
            severity: WARN
          }
        ]
      });

      healthModel();
      $httpBackend.flush();

      expect(healthSpy.calls.mostRecent().args[1]).toEqual({health: ERROR, count: 2 } );
    });

    it('should be in warn when 1 or more warn alerts are active', function () {
      expectReqRes({
        alert: [{
          severity: WARN
        }]
      });

      healthModel();
      $httpBackend.flush();
      expect(healthSpy.calls.mostRecent().args[1]).toEqual({ health: WARN, count: 1 });
    });

    it('should obey all the rules: highest error state wins.', function () {
      expectReqRes({
        alert: [
          {
            severity: ERROR
          },
          {
            severity: WARN
          }
        ]
      });

      healthModel();
      $httpBackend.flush();
      expect(healthSpy.calls.mostRecent().args[1]).toEqual({ health: ERROR, count: 2 });
    });
  });
});
