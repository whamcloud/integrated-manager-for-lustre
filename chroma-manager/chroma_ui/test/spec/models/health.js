//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

describe('Health model', function () {
  'use strict';

  var $httpBackend, healthSpy, WARN, ERROR, GOOD;

  beforeEach(module('constants', 'models', 'ngResource', 'services', 'interceptors', function ($provide) {
    // Mock out this dep.
    $provide.value('paging', jasmine.createSpy('paging'));
  }));

  var urls = {
    event: '/api/event/?dismissed=false&limit=1&severity__in=WARNING&severity__in=ERROR',
    alert: '/api/alert/?active=true&limit=0&severity__in=WARNING&severity__in=ERROR',
    inactiveAlert: '/api/alert/?active=false&limit=1&severity__in=WARNING',
    command: '/api/command/?dismissed=false&errored=true&limit=1'
  };

  function expectReqRes(config) {
    config = config || {};

    Object.keys(urls).forEach(function (url) {
      $httpBackend
        .expectGET(urls[url])
        .respond({meta: {}, objects: config[url] || []});
    });
  }

  beforeEach(inject(function ($injector, $rootScope) {
    $httpBackend = $injector.get('$httpBackend');
    var STATES = $injector.get('STATES');
    WARN = STATES.WARN;
    ERROR = STATES.ERROR;
    GOOD = STATES.GOOD;

    healthSpy = jasmine.createSpy('health');
    var scope = $rootScope.$new();
    scope.$on('health', healthSpy);
  }));

  afterEach(function () {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  });

  describe('working with health', function () {
    var healthModel;
    var flush;

    beforeEach(inject(function ($injector) {
      healthModel = $injector.get('healthModel');
      var $timeout = $injector.get('$timeout');

      flush = function () {
        $timeout.flush();
        $httpBackend.flush();
      };
    }));

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

    it('should listen for checkHealth events', function () {
      expectReqRes();
      flush();
      expect(healthSpy.callCount).toBe(1);
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

    it('should be in warn when 1 or more WARN alerts are inactive but have not been dismissed', function() {
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

    it('should be in warn when there are  1 or more unacknowledged failed commands: amber', function () {
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
});
