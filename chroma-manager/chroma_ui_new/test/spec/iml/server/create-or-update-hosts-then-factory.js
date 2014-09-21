describe('create or update hosts then', function () {
  'use strict';


  var requestSocket, postDeferred, putDeferred;
  beforeEach(module('server', function ($provide, $exceptionHandlerProvider) {
    $exceptionHandlerProvider.mode('log');

    requestSocket = jasmine.createSpy('requestSocket').andReturn({
      sendPost: jasmine.createSpy('sendPost'),
      sendPut: jasmine.createSpy('sendPut'),
      end: jasmine.createSpy('end')
    });
    $provide.value('requestSocket', requestSocket);

    $provide.decorator('requestSocket', function ($q, $delegate) {
      postDeferred = $q.defer();
      putDeferred = $q.defer();

      $delegate.plan().sendPost.andReturn(postDeferred.promise);
      $delegate.plan().sendPut.andReturn(putDeferred.promise);

      return $delegate;
    });
  }));

  var $rootScope, $exceptionHandler, createOrUpdateHostsThen, serverSpark, server, promise, handler, spy;
  beforeEach(inject(function (_$rootScope_, _$exceptionHandler_, _createOrUpdateHostsThen_) {
    $rootScope = _$rootScope_;
    $exceptionHandler = _$exceptionHandler_;
    createOrUpdateHostsThen = _createOrUpdateHostsThen_;

    spy = jasmine.createSpy('spy');

    serverSpark = {
      onceValue: jasmine.createSpy('onceValue')
    };

    server = {
      auth_type: 'existing_keys_choice',
      pdsh: 'storage[0-1].localdomain',
      address: [
        'storage0.localdomain',
        'storage1.localdomain'
      ]
    };

    promise = createOrUpdateHostsThen(server, serverSpark);

    handler = _.last(serverSpark.onceValue.mostRecentCall.args);
  }));

  it('should be a function', function () {
    expect(createOrUpdateHostsThen).toEqual(jasmine.any(Function));
  });

  it('should wait for data once on the serverSpark', function () {
    expect(serverSpark.onceValue).toHaveBeenCalledOnceWith('data', jasmine.any(Function));
  });

  it('should return a promise', function () {
    expect(promise).toEqual({
      then: jasmine.any(Function),
      catch: jasmine.any(Function),
      finally: jasmine.any(Function)
    });
  });

  describe('just posts', function () {
    beforeEach(function () {
      handler({
        body: {
          objects: []
        }
      });
    });

    it('should send a post through the spark', function () {
      expect(requestSocket.plan().sendPost).toHaveBeenCalledOnceWith('/host', {
        json: {
          objects: [
            {
              auth_type: 'existing_keys_choice',
              address: 'storage0.localdomain'
            },
            {
              auth_type: 'existing_keys_choice',
              address: 'storage1.localdomain'
            }
          ]
        }
      }, true);
    });

    it('should not send a put', function () {
      expect(requestSocket.plan().sendPut).not.toHaveBeenCalledOnce();
    });

    describe('response', function () {
      var response;

      beforeEach(function () {
        response = {
          body: {
            objects: [
              {command: {id: 1}, host: {id: 1, address: 'storage0.localdomain'}},
              {command: {id: 2}, host: {id: 2, address: 'storage1.localdomain'}}
            ]
          }
        };

        promise.then(spy);

        postDeferred.resolve(response);

        $rootScope.$digest();
      });

      it('should resolve with the expected response', function () {
        expect(spy).toHaveBeenCalledOnceWith(response);
      });

      it('should end the spark', function () {
        expect(requestSocket.plan().end).toHaveBeenCalledOnce();
      });
    });
  });

  describe('just puts', function () {
    beforeEach(function () {
      handler({
        body: {
          objects: [
            { address: 'storage0.localdomain', state: 'undeployed' },
            { address: 'storage1.localdomain', state: 'undeployed' }
          ]
        }
      });
    });

    it('should send a put through the spark', function () {
      expect(requestSocket.plan().sendPut).toHaveBeenCalledOnceWith('/host', {
        json: {
          objects: [
            { auth_type : 'existing_keys_choice', address : 'storage0.localdomain' },
            { auth_type : 'existing_keys_choice', address : 'storage1.localdomain' }
          ]
        }
      }, true);
    });

    it('should not send a post', function () {
      expect(requestSocket.plan().sendPost).not.toHaveBeenCalled();
    });

    describe('response fail', function () {
      var response;

      beforeEach(function () {
        response = {
          error: {
            message: 'boom'
          },
          body: {
            objects: []
          }
        };

        putDeferred.reject(response);

        $rootScope.$digest();
      });

      it('should throw the error', function () {
        expect($exceptionHandler.errors).toEqual([{
          message: 'boom'
        }]);
      });

      it('should end the spark', function () {
        expect(requestSocket.plan().end).toHaveBeenCalled();
      });
    });
  });

  describe('posts and puts', function () {
    beforeEach(function () {
      handler({
        body: {
          objects: [
            { address: 'storage0.localdomain', state: 'undeployed' }
          ]
        }
      });
    });

    it('should send a post through the spark', function () {
      expect(requestSocket.plan().sendPost).toHaveBeenCalledOnceWith('/host', {
        json: {
          objects: [
            { auth_type : 'existing_keys_choice', address : 'storage1.localdomain' }
          ]
        }
      }, true);
    });

    it('should send a put through the spark', function () {
      expect(requestSocket.plan().sendPut).toHaveBeenCalledOnceWith('/host', {
        json: {
          objects: [
            { auth_type : 'existing_keys_choice', address : 'storage0.localdomain' }
          ]
        }
      }, true);
    });

    describe('response', function () {
      beforeEach(function () {
        postDeferred.resolve({
          body: {
            objects: [
              {command: {id: 2}, host: {id: 2, address: 'storage1.localdomain'}}
            ]
          }
        });
        putDeferred.resolve({
          body: {
            objects: [
              {command: {id: 1}, host: {id: 1, address: 'storage0.localdomain'}}
            ]
          }
        });

        promise.then(spy);

        $rootScope.$digest();
      });

      it('should resolve with the expected response', function () {
        expect(spy).toHaveBeenCalledOnceWith({
          body: {
            objects: [
              {
                command: { id : 2 },
                host: {
                  id: 2,
                  address: 'storage1.localdomain'
                }
              },
              {
                command: { id : 1 },
                host: {
                  id: 1,
                  address: 'storage0.localdomain'
                }
              }
            ]
          }
        });
      });
    });
  });

  describe('nothing', function () {
    beforeEach(function () {
      handler({
        body: {
          objects: [
            { address: 'storage0.localdomain'},
            { address: 'storage1.localdomain'}
          ]
        }
      });
    });

    it('should not send a post', function () {
      expect(requestSocket.plan().sendPost).not.toHaveBeenCalled();
    });

    it('should not send a put', function () {
      expect(requestSocket.plan().sendPut).not.toHaveBeenCalled();
    });

    it('should resolve with the unused hosts', function () {
      promise.then(spy);

      $rootScope.$digest();

      expect(spy).toHaveBeenCalledOnceWith({
        body: {
          objects: [
            {
              host: { address: 'storage0.localdomain' }
            },
            {
              host: { address : 'storage1.localdomain' }
            }
          ]
        }
      });
    });
  });
});
