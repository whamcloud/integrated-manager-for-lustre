'use strict';

var testHostRouteFactory = require('../../../routes/test-host-route').wiretree;
var Q = require('q');
var _ = require('lodash-mixins');

describe('test host route ', function () {
  var testHostRoute, router, request, loop, logger,
    testHostDeferred, commandDeferred, jobDeferred, promise;

  beforeEach(function () {
    router = {
      post: jasmine.createSpy('post')
    };

    var deferred = Q.defer();
    promise = deferred.promise;

    spyOn(Q.makePromise.prototype, 'done').andCallFake(function () {
      this.then(function () {
        deferred.resolve();
      });
    });

    testHostDeferred = Q.defer();
    jobDeferred = Q.defer();
    commandDeferred = Q.defer();

    request = {
      get: jasmine.createSpy('get').andCallFake(function (path) {
        if (path === '/job')
          return jobDeferred.promise;
        else if (path === '/command')
          return commandDeferred.promise;
      }),
      post: jasmine.createSpy('post').andReturn(testHostDeferred.promise)
    };

    loop = jasmine.createSpy('loop').andReturn(jasmine.createSpy('finish'));

    logger = {
      child: jasmine.createSpy('child').andReturn({
        info: jasmine.createSpy('info'),
        debug: jasmine.createSpy('debug')
      })
    };

    testHostRoute = testHostRouteFactory(router, request, loop, logger, Q, _)();
  });

  it('should register a test host handler', function () {
    expect(router.post).toHaveBeenCalledOnceWith('/test_host', jasmine.any(Function));
  });

  describe('calling the route handler', function () {
    var handler, req, resp, next;

    beforeEach(function () {
      handler = router.post.mostRecentCall.args[1];

      req = {
        matches: [ '/test_host' ],
        verb: 'post',
        data: {
          json: {
            address:[
              'foo',
              'bar'
            ],
            auth_type:'existing_keys_choice'
          },
          method: 'post',
          headers: {
            Cookie: 'csrftoken=yGNhGrc6arLkQkMFHMAPbnFlCqHk0lGR; sessionid=2e9427f00bf25cd87048d08964348b22'
          }
        }
      };

      resp = {
        spark: {
          writeResponse: jasmine.createSpy('writeResponse'),
          writeError: jasmine.createSpy('writeError'),
          removeAllListeners: jasmine.createSpy('removeAllListeners'),
          on: jasmine.createSpy('on')
        }
      };

      handler(req, resp);

      next = jasmine.createSpy('next');
      loop.mostRecentCall.args[0](next);
    });

    it('should start a loop', function () {
      expect(loop).toHaveBeenCalledOnce();
    });

    it('should post to /test_host with data', function () {
      expect(request.post).toHaveBeenCalledOnceWith('/test_host', req.data);
    });

    it('should register an end listener on the spark when looping', function () {
      expect(resp.spark.on).toHaveBeenCalledOnceWith('end', jasmine.any(Function));
    });

    it('should remove all listeners on ending', function () {
      resp.spark.on.mostRecentCall.args[1]();

      expect(resp.spark.removeAllListeners).toHaveBeenCalledOnce();
    });

    it('should finish the loop', function () {
      resp.spark.on.mostRecentCall.args[1]();

      expect(loop.plan()).toHaveBeenCalledOnce();
    });

    describe('command', function () {
      beforeEach(function () {
        testHostDeferred.resolve({
          body: {
            objects: [
              {
                command: {
                  cancelled: false,
                  complete: true,
                  errored: false,
                  id: '1',
                  jobs: [
                    '/api/job/1/'
                  ]
                }
              },
              {
                command: {
                  cancelled: false,
                  complete: true,
                  errored: false,
                  id: '2',
                  jobs: [
                    '/api/job/2/'
                  ]
                }
              },
              {
                command: {
                  cancelled: false,
                  complete: true,
                  errored: false,
                  id: '3',
                  jobs: [
                    '/api/job/3/'
                  ]
                }
              }
            ]
          }
        });

        jobDeferred.resolve({
          statusCode: 200,
          body: {
            objects: [
              {
                step_results: {
                  '/api/step/1/': {
                    address: 'foo',
                    auth: false,
                    fqdn_matches: false,
                    fqdn_resolves: false,
                    hostname_valid: false,
                    openssl: false,
                    ping: false,
                    resolve: false,
                    reverse_ping: false,
                    reverse_resolve: false,
                    yum_can_update: false,
                    yum_valid_repos: false
                  }
                },
                steps: [ '/api/step/1/' ]
              },
              {
                step_results: {
                  '/api/step/2/': {
                    address: 'bar',
                    auth: false,
                    fqdn_matches: false,
                    fqdn_resolves: false,
                    hostname_valid: false,
                    openssl: false,
                    ping: false,
                    resolve: false,
                    reverse_ping: false,
                    reverse_resolve: false,
                    yum_can_update: false,
                    yum_valid_repos: false
                  }
                },
                steps: [ '/api/step/2/' ]
              },
              {
                step_results: {
                  '/api/step/3/': {
                    address: 'baz',
                    auth: false,
                    fqdn_matches: false,
                    fqdn_resolves: false,
                    hostname_valid: false,
                    openssl: false,
                    ping: false,
                    resolve: false,
                    reverse_ping: false,
                    reverse_resolve: false,
                    yum_can_update: false,
                    yum_valid_repos: false
                  }
                },
                steps: [ '/api/step/3/' ]
              }
            ]
          }
        });
      });

      it('should request the jobs from the command', function (done) {
        promise.then(function () {
          expect(request.get).toHaveBeenCalledOnceWith('/job', {
            jsonMask: 'objects(step_results,steps)',
            qs: {
              id__in: [ '1', '2', '3' ],
              limit: 0
            },
            headers: req.data.headers
          });

          done();
        });
      });

      it('should write the response for the jobs', function (done) {
        promise.then(function () {
          expect(resp.spark.writeResponse).toHaveBeenCalledOnceWith(200, {
            objects: [
              {
                address: 'foo',
                auth: false,
                fqdn_matches: false,
                fqdn_resolves: false,
                hostname_valid: false,
                openssl: false,
                ping: false,
                resolve: false,
                reverse_ping: false,
                reverse_resolve: false,
                yum_can_update: false,
                yum_valid_repos: false
              },
              {
                address: 'bar',
                auth: false,
                fqdn_matches: false,
                fqdn_resolves: false,
                hostname_valid: false,
                openssl: false,
                ping: false,
                resolve: false,
                reverse_ping: false,
                reverse_resolve: false,
                yum_can_update: false,
                yum_valid_repos: false
              },
              {
                address: 'baz',
                auth: false,
                fqdn_matches: false,
                fqdn_resolves: false,
                hostname_valid: false,
                openssl: false,
                ping: false,
                resolve: false,
                reverse_ping: false,
                reverse_resolve: false,
                yum_can_update: false,
                yum_valid_repos: false
              }
            ]
          });

          done();
        });
      });
    });
  });
});
