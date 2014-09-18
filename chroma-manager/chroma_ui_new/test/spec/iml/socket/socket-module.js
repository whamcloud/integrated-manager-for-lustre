describe('socket module', function () {
  'use strict';

  beforeEach(module('socket-module'));

  describe('socket', function () {
    var socket, $applyFunc, $document, $window, primus, runPipeline, spark;

    beforeEach(module(function ($provide) {
      $applyFunc = jasmine.createSpy('$applyFunc').andCallFake(_.identity);

      $provide.value('$applyFunc', $applyFunc);

      $window = {
        navigator: {
          userAgent: 'chrome'
        }
      };

      $provide.value('$window', $window);

      $document = [
        { cookie: 'csrftoken=yGNhGrc6arLkQkMFHMAPbnFlCqHk0lGT; sessionid=2fb9a3dced966d0b5b1e844d8d033d2e; ' +
          'HTTP_USER_AGENT: chrome;' }
      ];

      $provide.value('$document', $document);

      spark = {
        on: jasmine.createSpy('on'),
        removeListener: jasmine.createSpy('removeListener'),
        removeAllListeners: jasmine.createSpy('removeAllListeners'),
        emit: jasmine.createSpy('emit'),
        send: jasmine.createSpy('send')
      };

      primus = jasmine.createSpy('primus').andReturn({
        channel: jasmine.createSpy('channel').andReturn(spark),
        removeListener: jasmine.createSpy('removeListener'),
        on: jasmine.createSpy('on')
      });

      $provide.value('primus', primus);

      runPipeline = jasmine.createSpy('runPipeline');

      $provide.value('runPipeline', runPipeline);
    }));

    beforeEach(inject(function (_socket_) {
      socket = _socket_;
    }));

    it('should be a function', function () {
      expect(socket).toEqual(jasmine.any(Function));
    });

    describe('extended spark', function () {
      var extendedSpark;

      beforeEach(function () {
        extendedSpark = socket('request');
      });

      it('should be an object', function () {
        expect(extendedSpark).toEqual(jasmine.any(Object));
      });

      it('should come from a channel', function () {
        expect(primus.plan().channel).toHaveBeenCalledOnceWith('request');
      });

      it('should extend spark', function () {
        expect(Object.getPrototypeOf(extendedSpark)).toBe(spark);
      });

      it('should register a listener for reconnected', function () {
        expect(primus.plan().on).toHaveBeenCalledOnceWith('reconnected', jasmine.any(Function));
      });

      it('should have a way to set the last data', function () {
        expect(extendedSpark.setLastData).toEqual(jasmine.any(Function));
      });

      describe('on', function () {
        var off, handler;

        beforeEach(function () {
          handler = jasmine.createSpy('handler');
          handler.apply = jasmine.createSpy('apply');

          off = extendedSpark.on('data', handler);
        });

        it('should be a method', function () {
          expect(extendedSpark.on).toEqual(jasmine.any(Function));
        });

        it('should return an off function', function () {
          expect(off).toEqual(jasmine.any(Function));
        });

        it('should remove listener when calling off', function () {
          off();

          expect(spark.removeListener).toHaveBeenCalledOnceWith('data', jasmine.any(Function));
        });

        it('should register an on listener with spark', function () {
          expect(spark.on).toHaveBeenCalledOnceWith('data', jasmine.any(Function), jasmine.any(Object));
        });

        it('should call $applyFunc with a handler', function () {
          expect($applyFunc).toHaveBeenCalledOnceWith(jasmine.any(Function));
        });

        describe('data', function () {
          var response;

          beforeEach(function () {
            response = {
              statusCode: 200,
              body: { foo: 'bar' }
            };

            $applyFunc.mostRecentCall.args[0](response);
          });

          it('should set lastArgs to response', function () {
            expect(extendedSpark.lastArgs).toEqual([response]);
          });

          it('should apply the response to the handler', function () {
            expect(handler.apply).toHaveBeenCalledOnceWith({off: jasmine.any(Function)}, [response]);
          });
        });
      });

      describe('onValue', function () {
        var handler;

        beforeEach(function () {
          handler = function handler () {};

          handler.apply = jasmine.createSpy('apply');
          handler.call = jasmine.createSpy('call');
        });

        it('should be a method', function () {
          expect(extendedSpark.onValue).toEqual(jasmine.any(Function));
        });

        it('should call spark.on', function () {
          extendedSpark.onValue('data', handler);

          expect(spark.on).toHaveBeenCalledOnceWith('data', jasmine.any(Function), {off: jasmine.any(Function)});
        });

        it('should call handler directly with lastArgs', function () {
          var data = {
            statusCode: 200,
            body: { foo: 'bar' }
          };

          extendedSpark.setLastData(data);

          extendedSpark.onValue('data', handler);

          expect(handler.apply).toHaveBeenCalledOnceWith({off: jasmine.any(Function)}, [data]);
        });

        it('should only call handler directly for data or pipeline', function () {
          var data = {
            statusCode: 200,
            body: { foo: 'bar' }
          };

          extendedSpark.setLastData(data);

          extendedSpark.onValue('datum', handler);

          expect(handler.apply).not.toHaveBeenCalledOnce();
        });

        it('should wrap onValue with an existing pipeline', function () {
          var data = {
            statusCode: 200,
            body: { foo: 'bar' }
          };

          runPipeline.andCallFake(function (pipeline, response) {
            return _.compose.apply(_, pipeline.reverse())(response);
          });

          extendedSpark.addPipe(function (response) {
            response.body.bar = 'baz';

            return response;
          });

          extendedSpark.setLastData(data);

          extendedSpark.onValue('pipeline', handler);

          expect(handler.call).toHaveBeenCalledOnceWith({off: jasmine.any(Function )}, {
            statusCode: 200,
            body: {
              foo: 'bar',
              bar: 'baz'
            }
          });
        });
      });

      describe('addPipe', function () {
        var result, pipe, run;

        beforeEach(function () {
          pipe = jasmine.createSpy('pipe');
          result = extendedSpark.addPipe(pipe);
          run = spark.on.mostRecentCall.args[1];
        });

        it('should be a method', function () {
          expect(extendedSpark.addPipe).toEqual(jasmine.any(Function));
        });

        it('should return the extendedSpark', function () {
          expect(result).toEqual(extendedSpark);
        });

        it('should register a data listener when adding a pipe', function () {
          expect(spark.on).toHaveBeenCalledOnceWith('data', jasmine.any(Function), { off: jasmine.any(Function) });
        });

        describe('run', function () {
          var response;

          beforeEach(function () {
            response = {
              statusCode: 200,
              body: { foo: 'bar' }
            };
          });

          it('should run pipeline when data comes in', function () {
            run(response);

            expect(runPipeline).toHaveBeenCalledOnceWith([pipe, jasmine.any(Function)], response);
          });

          it('should emit pipeline as the last pipe', function () {
            run(response);

            runPipeline.mostRecentCall.args[0][1](response);

            expect(spark.emit).toHaveBeenCalledOnceWith('pipeline', response);
          });

          it('should not run pipeline for primus-emitter data', function () {
            run({type: 1});

            expect(runPipeline).not.toHaveBeenCalled();
          });
        });
      });

      describe('send', function () {
        var ack, result;

        beforeEach(function () {
          ack = jasmine.createSpy('ack');

          result = extendedSpark.send('req', { path: '/host' }, ack);
        });

        it('should be a method', function () {
          expect(extendedSpark.send).toEqual(jasmine.any(Function));
        });

        it('should return the extendedSpark', function () {
          expect(result).toEqual(extendedSpark);
        });

        it('should call spark with args plus auth header', function () {
          expect(spark.send).toHaveBeenCalledOnceWith('req', {
            path: '/host',
            options: {
              headers: {
                Cookie: 'csrftoken=yGNhGrc6arLkQkMFHMAPbnFlCqHk0lGT; sessionid=2fb9a3dced966d0b5b1e844d8d033d2e; \
HTTP_USER_AGENT: chrome;',
                'User-Agent': 'chrome',
                'X-CSRFToken': 'yGNhGrc6arLkQkMFHMAPbnFlCqHk0lGT; sessionid=2fb9a3dced966d0b5b1e844d8d033d2e; \
HTTP_USER_AGENT: chrome'
              }
            }
          }, ack);
        });
      });

      describe('end', function () {
        beforeEach(function () {
          spark.on.mostRecentCall.args[1]();
        });

        it('should register a listener on spark', function () {
          expect(spark.on).toHaveBeenCalledOnceWith('end', jasmine.any(Function));
        });

        it('should remove the reconnected listener on primus', function () {
          expect(primus.plan().removeListener).toHaveBeenCalledOnceWith('reconnected', jasmine.any(Function));
        });

        it('should remove all listeners from spark', function () {
          expect(spark.removeAllListeners).toHaveBeenCalledOnce();
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

  describe('runPipeline', function () {
    var runPipeline, pipe, response, pipeline;

    beforeEach(inject(function (_runPipeline_) {
      runPipeline = _runPipeline_;

      pipe = jasmine.createSpy('pipe');
      pipeline = [pipe];

      response = {foo: 'bar'};
    }));

    it('should be a function', function () {
      expect(runPipeline).toEqual(jasmine.any(Function));
    });

    it('should call a pipe with a given response', function () {
      runPipeline(pipeline, response);

      expect(pipe).toHaveBeenCalledOnceWith(response);
    });

    it('should call an async pipe with next', function () {
      runPipeline([asyncPipe, pipe], response);

      expect(pipe).toHaveBeenCalledOnceWith({ bar: 'baz' });

      function asyncPipe (response, next) {
        next({ bar: 'baz' });
      }
    });
  });
});
