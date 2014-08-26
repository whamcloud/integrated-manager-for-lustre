describe('run server action', function () {
  'use strict';

  var socket, action;

  beforeEach(module('server', function ($provide) {
    socket = jasmine.createSpy('socket').andReturn({
      send: jasmine.createSpy('send')
    });

    $provide.value('socket', socket);
  }));

  var runServerAction;

  beforeEach(inject(function (_runServerAction_) {
    action = {
      message: 'foo',
      convertToJob: function convertToJob () {
        return 'bar';
      }
    };

    runServerAction = _runServerAction_;
    runServerAction(action, []);
  }));

  it('should be a function', function () {
    expect(runServerAction).toEqual(jasmine.any(Function));
  });

  it('should get the spark', function () {
    expect(socket).toHaveBeenCalledOnceWith('request');
  });

  it('should send a post', function () {
    expect(socket.plan().send).toHaveBeenCalledOnceWith('req', {
      path: '/command',
      options: {
        method: 'post',
        json: {
          message: 'foo',
          jobs: 'bar'
        }
      }
    }, jasmine.any(Function));
  });

  describe('ack', function () {
    var handler;

    beforeEach(function () {
      handler = socket.plan().send.mostRecentCall.args[2];
    });

    it('should throw an error if one is passed', function () {
      var response = {
        error: 'baz'
      };

      expect(shouldThrow).toThrow();

      function shouldThrow () {
        handler(response);
      }
    });
  });
});
