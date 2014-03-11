'use strict';

var notificationsResourceModule = require('../../../resources/notification-resource'),
  notificationsResourceFactory = notificationsResourceModule.notificationResourceFactory,
  STATES = notificationsResourceModule.STATES,
  Q = require('q');

describe('Notifications resource', function () {
  var NotificationsResource, notificationsResource, Resource, AlertResource, EventResource, CommandResource;

  beforeEach(function () {
    Resource = createResource('resource');
    AlertResource = createResource('alert');
    EventResource = createResource('event');
    CommandResource = createResource('command');

    NotificationsResource = notificationsResourceFactory(Resource, AlertResource, CommandResource, EventResource, Q);
    notificationsResource = new NotificationsResource();
  });

  it('should call the Resource', function () {
    expect(Resource.call).toHaveBeenCalledOnceWith(notificationsResource, 'notification');
  });

  describe('get health', function () {
    describe('finding alerts', function () {
      beforeEach(function () {
        notificationsResource.httpGetHealth();
      });

      it('should look for active alerts', function () {
        expect(AlertResource.prototype.httpGetList).toHaveBeenCalledOnceWith({
          qs: {
            active: true,
            severity__in: [STATES.WARN, STATES.ERROR],
            limit: 0
          }
        });
      });

      it('should look for inactive alerts', function () {
        expect(AlertResource.prototype.httpGetList).toHaveBeenCalledOnceWith({
          qs: {
            active: false,
            dismissed: false,
            severity__in: STATES.WARN,
            limit: 1
          }
        });
      });

      it('should look for events', function () {
        expect(EventResource.prototype.httpGetList).toHaveBeenCalledOnceWith({
          qs: {
            dismissed: false,
            severity__in: [STATES.WARN, STATES.ERROR],
            limit: 1
          }
        });
      });

      it('should look for commands', function () {
        expect(CommandResource.prototype.httpGetList).toHaveBeenCalledOnceWith({
          qs: {
            errored: true,
            dismissed: false,
            limit: 1
          }
        });
      });
    });

    it('should be in error when 1 or more error alerts are active', function (done) {
      AlertResource._configureSpy([
        {
          severity: STATES.ERROR
        },
        {
          severity: STATES.WARN
        }
      ], {
        active: true,
        severity__in: [STATES.WARN, STATES.ERROR],
        limit: 0
      });

      notificationsResource.httpGetHealth().then(function then (state) {
        expect(state).toEqual({ body : STATES.ERROR });

        done();
      });
    });

    it('should be in warn when 1 or more warn alerts are active', function (done) {
      AlertResource._configureSpy([{
        severity: STATES.WARN
      }],
      {
        active: true,
        severity__in: [STATES.WARN, STATES.ERROR],
        limit: 0
      });

      notificationsResource.httpGetHealth().then(function then (state) {
        expect(state).toEqual({ body : STATES.WARN });

        done();
      });
    });

    it('should be in warn when 1 or more WARN alerts are inactive but have not been dismissed', function (done) {
      AlertResource._configureSpy([{}],
      {
        active: false,
        dismissed: false,
        severity__in: STATES.WARN,
        limit: 1
      });

      notificationsResource.httpGetHealth().then(function then (state) {
        expect(state).toEqual({ body : STATES.WARN });

        done();
      });
    });

    it('should be in warn when there are 1 or more unacknowledged WARN or higher events', function (done) {
      EventResource._configureSpy([
        [
          {
            severity: STATES.WARN
          },
          {
            severity: STATES.ERROR
          }
        ]
      ]);

      notificationsResource.httpGetHealth().then(function then (state) {
        expect(state).toEqual({ body : STATES.WARN });

        done();
      });
    });

    it('should be in warn when 1 or more WARN alerts are inactive but have not been dismissed', function (done) {
      CommandResource._configureSpy([{}]);

      notificationsResource.httpGetHealth().then(function then (state) {
        expect(state).toEqual({ body : STATES.WARN });

        done();
      });
    });

    it('should obey all the rules: highest error state wins.', function (done) {
      AlertResource._configureSpy([
        {
          severity: STATES.ERROR
        }
      ], {
        active: true,
        severity__in: [STATES.WARN, STATES.ERROR],
        limit: 0
      });

      AlertResource._configureSpy([{}],
        {
          active: false,
          dismissed: false,
          severity__in: [STATES.WARN],
          limit: 1
        });

      EventResource._configureSpy([
        {
          severity: STATES.WARN
        },
        {
          severity: STATES.ERROR
        }
      ]);

      CommandResource._configureSpy([{}]);

      notificationsResource.httpGetHealth().then(function then (state) {
        expect(state).toEqual({ body : STATES.ERROR });

        done();
      });
    });
  });
});


/**
 * Given a name, creates a resource mock.
 * @param {String} name
 * @returns {Resource}
 */
function createResource (name) {
  function Resource() {
    Resource._configureSpy([]);
  }

  Resource.prototype.httpGetList = jasmine.createSpy(name + 'Resource.httpGetList');

  Resource._configureSpy = function _configureSpy(then, when) {
    if (when)
      Resource.prototype.httpGetList.when({qs: when}).thenReturn(Q.when({
        body: {
          objects: then
        }
      }));
    else
      Resource.prototype.httpGetList.andReturn(Q.when({
        body: {
          objects: then
        }
      }));
  };

  spyOn(Resource, 'call');

  return Resource;
}