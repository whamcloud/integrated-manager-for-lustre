'use strict';

var Q = require('q');
var notificationsResourceModule = require('../../../resources/notification-resource');
var notificationsResourceFactory = notificationsResourceModule.notificationResourceFactory;
var STATES = notificationsResourceModule.STATES;

describe('Notifications resource', function () {
  var NotificationsResource, notificationsResource, Resource, AlertResource;

  beforeEach(function () {
    Resource = createResource('resource');
    AlertResource = createResource('alert');

    NotificationsResource = notificationsResourceFactory(Resource, AlertResource);
    notificationsResource = new NotificationsResource();
  });

  it('should call the Resource', function () {
    expect(Resource.call).toHaveBeenCalledOnceWith(notificationsResource, 'notification');
  });

  describe('get health', function () {
    describe('finding notifications', function () {
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
        expect(state).toEqual({
          body: STATES.ERROR
        });

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
        expect(state).toEqual({
          body : STATES.WARN
        });

        done();
      });
    });

    it('should obey all the rules: highest error state wins.', function (done) {
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
  });

  it('should pass any params to the notification calls', function () {
    var authHeaders = {
      headers: {
        Cookie: 'csrftoken=F0bJQGBt7BmzAicFJiBnmTqbuywPjXUs; sessionid=6c6764465d25bdabd2f0f51cc832374b'
      }
    };

    notificationsResource.httpGetHealth(authHeaders);

    expect(AlertResource.prototype.httpGetList.calls[0].args[0]).toContainObject(authHeaders);
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
