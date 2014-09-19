describe('primus module', function () {
  'use strict';

  beforeEach(module('primus'));

  describe('Primus', function () {
    var $window, Primus, WebSocket, primus, disconnectModal, BASE;

    beforeEach(module(function ($provide) {
      disconnectModal = jasmine.createSpy('disconnectModal').andReturn({
        close: jasmine.createSpy('close')
      });
      $provide.value('disconnectModal', disconnectModal);

      $window = {
        location: { port: '8888' }
      };
      $provide.value('$window', $window);

      Primus = jasmine.createSpy('Primus').andReturn({
        on: jasmine.createSpy('on'),
        end: jasmine.createSpy('end')
      });
      $provide.value('Primus', Primus);

      WebSocket = _.noop;
      $provide.value('WebSocket', WebSocket);
    }, {
      BASE: 'localhost'
    }));

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
        expect(Primus.plan().on).toHaveBeenCalledWith('reconnecting', jasmine.any(Function));
      });

      it('should register an reconnected listener', function () {
        expect(Primus.plan().on).toHaveBeenCalledWith('reconnected', jasmine.any(Function));
      });

      it('should register three listeners (reconnecting, reconnected, and error)', function () {
        expect(Primus.plan().on.calls.length).toBe(3);
      });

      describe('reconnecting', function () {
        var onReconnecting;

        beforeEach(function () {
          onReconnecting = Primus.plan().on.mostRecentCallThat(function(call) {
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
            onReconnected = Primus.plan().on.mostRecentCallThat(function(call) {
              return call.args[0] === 'reconnected';
            }).args[1];

            onReconnected();
          });

          it('should close the modal', function () {
            expect(disconnectModal.plan().close).toHaveBeenCalledOnce();
          });

          it('should not close the modal when it\'s already closed', function () {
            onReconnected();

            expect(disconnectModal.plan().close).toHaveBeenCalledOnce();
          });
        });
      });

      describe('error handling', function () {
        var handler, err;

        beforeEach(function () {
          handler = _.last(Primus.plan().on.mostRecentCall.args);
          err = new Error('foo');
        });

        it('should return if the error is an empty WebSocket error event', function () {
          var err = {
            target: new WebSocket()
          };

          expect(handler(err)).toBeUndefined();
        });

        it('should end primus', function () {
          try {
            handler(err);
          } catch (error) {}
          finally {
            expect(Primus.plan().end).toHaveBeenCalledOnce();
          }
        });

        it('should throw the error', function () {
          expect(shouldThrow).toThrow(err);

          function shouldThrow () {
            handler(err);
          }
        });
      });
    });
  });

  describe('$applyFunc', function () {

    var $rootScope;

    beforeEach(module(function ($provide) {
      $rootScope = {
        $apply: jasmine.createSpy('$apply').andCallFake(function (apply) {
          apply();
        })
      };

      $provide.value('$rootScope', $rootScope);
    }));

    var $applyFunc, func, apply;

    beforeEach(inject(function (_$applyFunc_) {
      $applyFunc = _$applyFunc_;

      func = jasmine.createSpy('func');
      apply = $applyFunc(func);
    }));

    it('should be a function', function () {
      expect($applyFunc).toEqual(jasmine.any(Function));
    });

    it('should return a function', function () {
      expect($applyFunc(func)).toEqual(jasmine.any(Function));
    });

    describe('not in $$phase', function () {
      beforeEach(function () {
        apply('foo', 'bar');
      });

      it('should $apply', function () {
        expect($rootScope.$apply).toHaveBeenCalledOnceWith(jasmine.any(Function));
      });

      it('should call func', function () {
        expect(func).toHaveBeenCalledOnceWith('foo', 'bar');
      });
    });

    it('should call func if $rootScope is in $$phase', function () {
      $rootScope.$$phase = '$apply';

      apply('bar', 'baz');

      expect(func).toHaveBeenCalledOnceWith('bar', 'baz');
    });
  });
});