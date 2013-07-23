describe('Health model', function () {
  'use strict';

  var $httpBackend;
  var healthSpy;
  var WARN;
  var ERROR;
  var GOOD;
  var healthModel;
  var flush;

  var urls = {
    event: '/api/event/?dismissed=false&limit=1&severity__in=WARNING&severity__in=ERROR',
    alert: '/api/alert/?active=true&limit=0&severity__in=WARNING&severity__in=ERROR',
    inactiveAlert: '/api/alert/?active=false&dismissed=false&limit=1&severity__in=WARNING',
    command: '/api/command/?dismissed=false&errored=true&limit=1'
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

    // Spy on $q.all to make sure all expected api calls are being waited on.
    $provide.decorator('$q', function ($delegate) {
      spyOn($delegate, 'all').andCallThrough();

      return $delegate;
    });
  }));

  beforeEach(inject(function (_$httpBackend_, _STATES_, _healthModel_, $timeout, $rootScope) {
    $httpBackend = _$httpBackend_;
    WARN = _STATES_.WARN;
    ERROR = _STATES_.ERROR;
    GOOD = _STATES_.GOOD;

    healthSpy = jasmine.createSpy('health');
    var scope = $rootScope.$new();
    scope.$on('health', healthSpy);

    healthModel = _healthModel_;

    flush = function flusher() {
      $timeout.flush();
      $httpBackend.flush();
    };
  }));

  afterEach(function () {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  });

  describe('working with health', function () {
    it('should broadcast a health event as a listening mechanism', function () {
      expectReqRes();
      flush();
      expect(healthSpy).toHaveBeenCalledWith(jasmine.any(Object), GOOD);
    });

    it('should provide a timeout that periodically emits a health event', function () {
      expectReqRes();
      flush();
      expect(healthSpy.callCount).toBe(1);
    });

    it('should register another timeout after the first one fires', function () {
      expectReqRes();
      flush();
      expectReqRes();
      flush();
      expect(healthSpy.callCount).toBe(2);
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
      flush();
      expect(healthSpy.mostRecentCall.args[1]).toBe(ERROR);
    });

    it('should be in warn when 1 or more warn alerts are active', function () {
      expectReqRes({
        alert: [{
          severity: WARN
        }]
      });
      flush();
      expect(healthSpy.mostRecentCall.args[1]).toBe(WARN);
    });

    it('should be in warn when 1 or more WARN alerts are inactive but have not been dismissed', function () {
      expectReqRes({
        inactiveAlert: [{}]
      });
      flush();
      expect(healthSpy.mostRecentCall.args[1]).toBe(WARN);
    });

    it('should be in warn when there are 1 or more unacknowledged WARN or higher events', function () {
      expectReqRes({
        event: [
          {
            severity: WARN
          },
          {
            severity: ERROR
          }
        ]
      });
      flush();
      expect(healthSpy.mostRecentCall.args[1]).toBe(WARN);
    });

    it('should be in warn when there are 1 or more unacknowledged failed commands: amber', function () {
      expectReqRes({
        command: [{}]
      });
      flush();
      expect(healthSpy.mostRecentCall.args[1]).toBe(WARN);
    });

    it('should obey all the rules: highest error state wins.', function () {
      expectReqRes({
        alert: [
          {
            severity: ERROR
          }
        ],
        inactiveAlert: [{}],
        event: [
          {
            severity: WARN
          },
          {
            severity: ERROR
          }
        ],
        command: [{}]
      });
      flush();
      expect(healthSpy.mostRecentCall.args[1]).toBe(ERROR);
    });
  });

  describe('promise resolution', function () {
    it('should wait for all calls to resolve', inject(function ($q) {
      expectReqRes();
      flush();

      expect($q.all.callCount).toBe(1);
      expect($q.all.mostRecentCall.args[0].length).toEqual(Object.keys(urls).length);
    }));
  });
});
