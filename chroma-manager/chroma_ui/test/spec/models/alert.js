describe('Alerts model', function () {
  'use strict';

  var apiName = '/api/alert/';

  var fixture = {
    active: true,
    affected: [
      {
        content_type_id: 61,
        id: 8,
        resource_uri: '/api/target/8/'
      },
      {
        content_type_id: 79,
        id: 1,
        resource_uri: '/api/filesystem/1/'
      }
    ],
    alert_item: '/api/target/8/',
    alert_item_content_type_id: 61,
    alert_item_id: 8,
    alert_item_str: 'testfs-OST0005',
    alert_type: 'TargetOfflineAlert',
    begin: '2013-08-28T13:28:27.185069+00:00',
    dismissed: false,
    end: '2013-08-28T13:28:27.185069+00:00',
    id: '25',
    message: 'Target testfs-OST0005 offline',
    resource_uri: '/api/alert/25/',
    severity: 'ERROR'
  };

  beforeEach(module('models', 'ngResource', 'constants', 'services'));

  afterEach(inject(function ($httpBackend) {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  }));

  it('should return the resource', inject(function (alertModel) {
    expect(alertModel).toBeDefined();
    expect(alertModel).toEqual(jasmine.any(Function));
  }));

  it('should return the state', inject(function (alertModel, $httpBackend, STATES) {
    $httpBackend.expectGET(apiName).respond(fixture);

    var model = alertModel.get();

    $httpBackend.flush();

    expect(model.getState()).toEqual(STATES.ERROR);
  }));

  it('should tell if it\'s dismissable', inject(function (alertModel, $httpBackend, STATES) {
    function testBehavior(expectFunc, overrides) {
      var cloned = _.clone(fixture);
      _.extend(cloned, overrides || {});

      $httpBackend.expectGET(apiName).respond(cloned);

      var model = alertModel.get();

      $httpBackend.flush();

      expectFunc(expect(model.notDismissable()));
    }

    testBehavior(function (expect) {
      expect.toBeTruthy();
    });

    testBehavior(function (expect) {
      expect.toBeTruthy();
    }, {severity: STATES.WARN});

    testBehavior(function (expect) {
      expect.toBeFalsy();
    }, {severity: STATES.INFO});

    testBehavior(function (expect) {
      expect.toBeFalsy();
    }, {severity: STATES.ERROR, active: false});

    testBehavior(function (expect) {
      expect.toBeFalsy();
    }, {severity: STATES.WARN, active: false});
  }));

  it('should return a no dismiss message key', inject(function (alertModel, $httpBackend) {
    $httpBackend.expectGET(apiName).respond(fixture);

    var model = alertModel.get();

    $httpBackend.flush();

    expect(model.noDismissMessage()).toEqual('no_dismiss_message_alert');
  }));
});
