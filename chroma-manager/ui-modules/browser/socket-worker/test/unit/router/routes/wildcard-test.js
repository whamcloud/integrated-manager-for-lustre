'use strict';

var proxyquire = require('proxyquire').noPreserveCache();

describe('routes wildcard', function () {
  var router, wildcard;

  beforeEach(function () {
    router = {
      all: jasmine.createSpy('all')
    };

    wildcard = proxyquire('../../../../router/routes/wildcard', {
      '../index': router
    });

    wildcard();
  });

  it('should call router.all', function () {
    expect(router.all).toHaveBeenCalledOnceWith('/(.*)', jasmine.any(Function));
  });

  describe('generic handler', function () {
    var req, resp, next;

    beforeEach(function () {
      req = {
        data: {
          ack: 'ack',
          payload: 'payload'
        }
      };

      resp = {
        write: 'write',
        socket: {
          sendMessage: jasmine.createSpy('resp.socket.sendMessage'),
          onMessage: jasmine.createSpy('resp.socket.onMessage')
        }
      };

      next = jasmine.createSpy('next');
    });

    describe('with ack', function () {
      beforeEach(function () {
        router.all.calls.mostRecent().args[1](req, resp, next);
      });

      it('should send a message when the data contains an ack', function () {
        expect(resp.socket.sendMessage).toHaveBeenCalledOnceWith(req.data.payload, resp.write);
      });

      it('should not call onMessage', function () {
        expect(resp.socket.onMessage).not.toHaveBeenCalled();
      });

      it('should call next', function () {
        expect(next).toHaveBeenCalledOnceWith(req, resp);
      });
    });

    describe('with no ack', function () {
      beforeEach(function () {
        delete req.data.ack;
        router.all.calls.mostRecent().args[1](req, resp, next);
      });

      it('should call onMessage', function () {
        expect(resp.socket.onMessage).toHaveBeenCalledOnceWith(resp.write);
      });

      it('should call send message', function () {
        expect(resp.socket.sendMessage).toHaveBeenCalledOnceWith(req.data.payload, undefined);
      });

      it('should call next', function () {
        expect(next).toHaveBeenCalledOnceWith(req, resp);
      });
    });
  });
});
