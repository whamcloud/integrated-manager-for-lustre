'use strict';

var rewire = require('rewire');
var requestAgent = rewire('../request-agent');
var https = require('https');

describe('request agent', function () {

  describe('agent', function () {
    var agent;
    beforeEach(function () {
      agent = requestAgent.agent;
    });

    it('should initialize a new agent', function () {
      expect(agent instanceof https.Agent).toBe(true);
    });

    it('should reject unauthorized', function () {
      expect(agent.options.rejectUnauthorized).toBe(false);
    });

    it('should have infinite maxSockets', function () {
      expect(agent.options.maxSockets).toBe(Infinity);
    });
  });

  describe('waitForRequests', function () {
    var revert, clearInterval, agent, setInterval, spy, fn;
    beforeEach(function () {
      agent = {
        sockets: {socket1: {}}
      };
      clearInterval = jasmine.createSpy('clearInterval');
      setInterval = jasmine.createSpy('setInterval');

      revert = requestAgent.__set__({
        module: {
          exports: {
            agent: agent
          }
        },
        clearInterval: clearInterval,
        setInterval: setInterval
      });

      spy = jasmine.createSpy('spy');

      setInterval.and.callFake(function (cb) {
        fn = cb;
      });

      requestAgent.waitForRequests(spy);
    });

    afterEach(function () {
      revert();
    });

    it('should turn every 10 seconds', function () {
      expect(setInterval).toHaveBeenCalledOnceWith(jasmine.any(Function), 10);
    });

    describe('with sockets', function () {
      beforeEach(function () {
        fn();
      });

      it('should not call the done function if sockets still exist', function () {
        expect(spy).not.toHaveBeenCalled();
      });

      it('should not call clearInterval if sockets still exist', function () {
        expect(clearInterval).not.toHaveBeenCalled();
      });
    });

    describe('without sockets', function () {
      beforeEach(function () {
        agent.sockets = {};
        fn();
      });

      it('should call the done function if there are no more sockets', function () {
        expect(spy).toHaveBeenCalledOnce();
      });

      it('should clear the interval if there are no more sockets', function () {
        expect(clearInterval).toHaveBeenCalledOnce();
      });
    });
  });
});
