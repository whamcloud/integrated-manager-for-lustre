describe('notification model', function () {
  'use strict';

  beforeEach(module('models', function ($provide) {
    $provide.value('baseModel', jasmine.createSpy('baseModel').andReturn({
      query: jasmine.createSpy('query')
    }));
    $provide.value('paging', jasmine.createSpy('paging'));
    $provide.value('alertModel', jasmine.createSpy('alertModel'));
    $provide.value('eventModel', jasmine.createSpy('eventModel'));
    $provide.value('commandModel', jasmine.createSpy('commandModel'));
  }));

  var baseModel, notificationModel, alertModel, commandModel, eventModel, paging;

  beforeEach(inject(function (_baseModel_, _notificationModel_, _alertModel_, _commandModel_, _eventModel_, _paging_) {
    notificationModel = _notificationModel_;
    baseModel = _baseModel_;
    alertModel = _alertModel_;
    commandModel = _commandModel_;
    eventModel = _eventModel_;
    paging = _paging_;
  }));

  it('should setup the model as expected', function () {
    expect(baseModel).toHaveBeenCalledOnceWith({
      url: '/api/notification',
      actions: {
        dismissAll: {
          url: '/api/notification/dismiss_all',
          method: 'PUT',
          isArray: false
        },
        query: {
          method: 'GET',
          isArray: true,
          interceptor: {
            response: jasmine.any(Function)
          }
        }
      }
    });
  });

  describe('intercepting responses', function () {
    var command, event, alert, meta;

    beforeEach(function () {
      command = {
        type: 'Command'
      };

      alert = {
        type: 'AlertState'
      };

      event = {
        type: 'Event'
      };

      meta = {
        limit: 30,
        next: null,
        offset: 0,
        previous: '/api/notification/?limit=30&offset=0&order_by=-created_at&dismissed=false',
        total_count: 3
      };

      baseModel.mostRecentCall.args[0].actions.query.interceptor.response({
        data: [
          command,
          alert,
          event
        ],
        props: {
          meta: meta
        }
      });
    });

    it('should create a new command', function () {
      expect(commandModel).toHaveBeenCalledOnceWith(command);
    });

    it('should create a new alert', function () {
      expect(alertModel).toHaveBeenCalledOnceWith(alert);
    });

    it('should create a new event', function () {
      expect(eventModel).toHaveBeenCalledOnceWith(event);
    });

    it('should setup paging', function () {
      expect(paging).toHaveBeenCalledOnceWith(meta);
    });
  });
});
