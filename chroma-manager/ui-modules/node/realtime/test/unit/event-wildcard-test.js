'use strict';

var rewire = require('rewire');
var eventWildcard = rewire('../../event-wildcard');

describe('event wildcard', function () {
  var revert, emit, socket, acker, next;

  beforeEach(function () {
    emit = {
      apply: jasmine.createSpy('apply')
    };

    revert = eventWildcard.__set__({
      emit: emit
    });

    acker = {};

    socket = {
      ack: jasmine.createSpy('ack').and.returnValue(acker)
    };

    next = jasmine.createSpy('next');

    eventWildcard(socket, next);
  });

  afterEach(function () {
    revert();
  });

  it('should call next', function () {
    expect(next).toHaveBeenCalledOnce();
  });

  it('should override socket.onevent', function () {
    expect(socket.onevent).toEqual(jasmine.any(Function));
  });

  describe('socket.onevent', function () {
    var packet;

    beforeEach(function () {
      packet = {};

    });

    it('should default to empty data', function () {
      socket.onevent(packet);

      expect(emit.apply).toHaveBeenCalledOnceWith(socket, []);
    });

    it('should call wildcard with empty data', function () {
      socket.onevent(packet);

      expect(emit.apply).toHaveBeenCalledOnceWith(socket, ['*', { eventName: undefined }]);
    });

    it('should push an ack if there is a packet.id', function () {
      packet.id = 2;
      packet.data = ['name', {}];
      socket.onevent(packet);

      expect(socket.ack).toHaveBeenCalledOnceWith(packet.id);
    });

    it('should emit the args', function () {
      packet.data = ['name', {}];
      socket.onevent(packet);

      expect(emit.apply).toHaveBeenCalledOnceWith(socket, ['name', {}]);
    });

    it('should emit wildcard args', function () {
      packet.data = ['name', {foo: 'bar'}];
      socket.onevent(packet);

      expect(emit.apply).toHaveBeenCalledOnceWith(socket, ['*', {foo: 'bar', eventName: 'name'}]);
    });
  });
});
