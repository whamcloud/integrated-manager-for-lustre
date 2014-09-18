describe('Primus', function () {
  'use strict';

  var Primus, primus, primusLibInstance, disconnectModal, disconnectModalInstance, BASE;

  beforeEach(module('primus'));

  mock.beforeEach('BASE', function createMocks() {
    primusLibInstance = {
      on: jasmine.createSpy('on')
    };

    Primus = jasmine.createSpy('primus').andCallFake(function () {
      return primusLibInstance;
    });

    disconnectModalInstance = {
      close: jasmine.createSpy('close')
    };

    disconnectModal = jasmine.createSpy('disconnectModal').andCallFake(function () {
      return disconnectModalInstance;
    });

    return [
      {
        name: 'Primus',
        value: Primus
      },
      {
        name: 'disconnectModal',
        value: disconnectModal
      },
      {
        name: '$window',
        value: {
          location: {
            port: '8888'
          }
        }
      }
    ];
  });

  beforeEach(inject(function (_primus_, _BASE_) {
    primus = _primus_;
    BASE = _BASE_;
  }));

  describe('setup', function () {
    var instance;

    beforeEach(function () {
      instance = primus();
    });

    it('should call the primus lib with the path', function () {
      expect(Primus).toHaveBeenCalledWith(BASE + ':8888');
    });

    it('should be a singleton', function () {
      var anotherInstance = primus();

      expect(instance).toBe(anotherInstance);
    });

    it('should register a reconnecting listener', function () {
      expect(primusLibInstance.on).toHaveBeenCalledWith('reconnecting', jasmine.any(Function));
    });

    it('should register a reconnected listener', function () {
      expect(primusLibInstance.on).toHaveBeenCalledWith('reconnected', jasmine.any(Function));
    });

    it('should register two listeners (reconnecting and reconnected)', function () {
      expect(primusLibInstance.on.calls.length).toBe(2);
    });

    describe('reconnecting', function () {
      var onReconnecting;

      beforeEach(function () {
        onReconnecting = primusLibInstance.on.mostRecentCallThat(function(call) {
          return call.args[0] === 'reconnecting';
        }).args[1];

        onReconnecting();
      });

      it('should start the disconnectModal', function () {
        expect(disconnectModal).toHaveBeenCalledOnce();
      });

      it('should not restart the disconnectModal when it\'s already open', function () {
        onReconnecting();

        expect(disconnectModal).toHaveBeenCalledOnce();
      });

      describe('reconnected', function () {
        var onReconnected;

        beforeEach(function () {
          onReconnected = primusLibInstance.on.mostRecentCallThat(function(call) {
            return call.args[0] === 'reconnected';
          }).args[1];

          onReconnected();
        });

        it('should close the modal', function () {
          expect(disconnectModalInstance.close).toHaveBeenCalledOnce();
        });

        it('should not close the modal when it\'s already closed', function () {
          onReconnected();

          expect(disconnectModalInstance.close).toHaveBeenCalledOnce();
        });
      });
    });
  });
});
