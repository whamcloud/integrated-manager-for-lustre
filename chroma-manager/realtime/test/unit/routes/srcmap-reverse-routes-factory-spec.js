'use strict';

var srcmapReverseRoutesFactory = require('../../../routes/srcmap-reverse-routes-factory');
var Q = require('q');

describe('srcmap-reverse reverse in realtime', function () {
  var handler, srcmapReverseRoutes, router, request, logger, srcmapReverse, promisedFile, req, resp, conf;
  var deferred;
  var flattened = '{"column":17000,"compiledLine":"at Object.DashboardFilterCtrl.$scope.filter.onFilterView \
(chroma_ui/built-b3de331a.js:38:17000)","line":38,"url":"https://localhost:8000/static/chroma_ui/built-b3de331a.js"}';

  beforeEach(function () {

    deferred = Q.defer();

    spyOn(Q.makePromise.prototype, 'done').andCallFake(function () {
      this.then(function () {
        deferred.resolve();
      });
    });

    router = {
      post: jasmine.createSpy('post')
    };

    request = {
      post: jasmine.createSpy('post')
    };

    logger = {
      info: jasmine.createSpy('info')
    };

    srcmapReverse = {
      execute: jasmine.createSpy('execute').andReturn('a reversed stack string')
    };

    conf = {
      sourceMapDir: 'chroma-manager/chroma_ui_new/static/chroma_ui/built*.map'
    };

    promisedFile = {
      getFile: jasmine.createSpy('getFile').andCallFake(function (dir) {
        return Q.resolve(dir);
      })
    };

    resp = {
      ack: jasmine.createSpy('ack'),
      spark: {
        getResponseFormat: jasmine.createSpy('getResponseFormat'),
        getErrorFormat: jasmine.createSpy('getErrorFormat')
      }
    };
  });

  describe('send client error', function () {

    beforeEach(function () {
      srcmapReverseRoutes = srcmapReverseRoutesFactory(router, request, logger, srcmapReverse, promisedFile, conf);
      srcmapReverseRoutes();
      handler = router.post.mostRecentCall.args[1];

    });

    describe('happy path', function () {

      beforeEach(function () {

        req = {
          path: '/srcmap-reverse',
          data: {
            method: 'post',
            cause: 'spec happy path',
            message: 'spec happy path',
            stack: 'some stack string',
            url: 'https://localhost:8000/ui/',
            headers: {
              Cookie: 'csrftoken=someToken; sessionid=someSessionID; HTTP_USER_AGENT: chrome;',
              HTTP_USER_AGENT: 'chrome',
              'X-CSRFToken': 'someToken; sessionid=2fb9a3dced966d0b5b1e844d8d033d2e; HTTP_USER_AGENT: chrome'
            }
          }
        };

        handler(req, resp);
      });

      it('should register a srcmap-reverse handler', function () {
        expect(router.post).toHaveBeenCalledOnceWith('/srcmap-reverse', jasmine.any(Function));
      });

      it('should call the logger', function () {
        expect(logger.info).toHaveBeenCalledWith('srcmap-reverse req rcvd');
      });

      it('should call getFile with a string', function () {
        expect(promisedFile.getFile).toHaveBeenCalledWith(conf.sourceMapDir);
      });

      it('should call execute', function (done) {
        deferred.promise.then(function () {
          expect(srcmapReverse.execute).toHaveBeenCalledWith('some stack string', conf.sourceMapDir);

          done();
        });
      });

      it('should call resp.spark.getResponseFormat', function (done) {
        deferred.promise.then(function () {
          expect(resp.spark.getResponseFormat).toHaveBeenCalledWith(201, { data: 'a reversed stack string' });

          done();
        });
      });

      it('should call resp.ack', function (done) {
        deferred.promise.then(function () {
          expect(resp.ack).toHaveBeenCalledWith(resp.spark.getResponseFormat(201, {data: flattened}));

          done();
        });
      });

      it('should set req.data.stack', function (done) {
        deferred.promise.then(function () {
          expect(req.data.stack).toEqual('a reversed stack string');

          done();
        });
      });

      it('should call request.post with appropriate body', function (done) {
        deferred.promise.then(function () {

          expect(request.post).toHaveBeenCalledWith('client_error/', {
              json: {
                method: 'post',
                cause: 'spec happy path',
                message: 'spec happy path',
                stack: 'a reversed stack string',
                url: 'https://localhost:8000/ui/'
              },
              headers: {
                Cookie: 'csrftoken=someToken; sessionid=someSessionID; HTTP_USER_AGENT: chrome;',
                HTTP_USER_AGENT: 'chrome',
                'X-CSRFToken': 'someToken; sessionid=2fb9a3dced966d0b5b1e844d8d033d2e; HTTP_USER_AGENT: chrome'
              }
            }
          );

          done();
        });
      });
    });

    describe('incorrect input', function () {
      beforeEach(function () {
        srcmapReverse.execute.andCallFake(function () {
          throw new Error('srcmapReverse.execute error');
        });

        handler(req, resp);
      });

      it('should call resp.spark.getErrorFormat', function (done) {
        deferred.promise.then(function () {
          expect(resp.spark.getErrorFormat).toHaveBeenCalledWith(500, {});

          done();
        });
      });

      it('should call resp.ack', function (done) {
        deferred.promise.then(function () {
          expect(resp.ack).toHaveBeenCalledWith(resp.spark.getErrorFormat(500, 'srcmapReverse.execute error'));

          done();
        });
      });

    });
  });

});
