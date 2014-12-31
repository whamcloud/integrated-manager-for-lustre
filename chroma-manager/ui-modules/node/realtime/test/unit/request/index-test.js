'use strict';

var rewire = require('rewire');
var requestIndex = rewire('../../../request');
var PassThrough = require('stream').PassThrough;
var λ = require('highland');
var _ = require('lodash-mixins');

describe('request', function () {
  var request, r, s, req, revert, onResponse;
  beforeEach(function () {

    req = new PassThrough();
    req.setHeader = jasmine.createSpy('setHeader');
    r = new PassThrough();
    onResponse = _.noop;

    request = jasmine.createSpy('request').and.callFake(function (options, fn) {
      process.nextTick(_.flow(_.partial(fn, r), onResponse));

      return req;
    });

    revert = requestIndex.__set__({
      request: request
    });
  });

  afterEach(function () {
    revert();
  });

  describe('the request', function () {
    var buffer;

    beforeEach(function () {
      buffer = 'buffer';
      s = requestIndex('/api/alert/', buffer);
    });

    it('should call setHeader on the request', function (done) {
      λ(req)
        .errors(done.fail)
        .each(function () {
          expect(req.setHeader).toHaveBeenCalledOnceWith('content-length', buffer.length);

          done();
        });
    });

    it('should write the buffer to the request', function (done) {
      λ(req)
        .errors(done.fail)
        .each(function (data) {
          expect(data + '').toEqual(buffer);
          done();
        });
    });

    it('should handle errors on the request', function (done) {
      var err = new Error('error on request');

      λ(s)
        .errors(function (e) {
          expect(e).toEqual(err);
          done();
        })
        .each(_.noop);

      req.emit('error', err);
    });

    it('should end', function (done) {
      var spy = jasmine.createSpy('spy');

      req.once('end', spy);
      req.once('end', function () {
        expect(spy).toHaveBeenCalledOnce();
        done();
      });
      req.once('error', done.fail);
      req.read();
    });
  });

  describe('the response', function () {
    it('should receive the chunk on the response stream', function (done) {
      var chunk = 'test';
      s = requestIndex('/api/alert/', 'buffer');
      r.write(chunk);
      r.end();

      λ(s)
        .errors(done.fail)
        .each(function (data) {
          expect(data + '').toEqual(chunk);

          done();
        });
    });

    it('should handle error when status code is greater than 400', function (done) {
      r.statusCode = 404;
      s = requestIndex('/api/alert/', 'buffer');
      λ(s)
        .errors(function (e) {
          expect(e.statusCode).toEqual(404);
          done();
        })
        .each(_.noop);
    });

    describe('passthrough error', function () {
      var err;
      beforeEach(function () {
        err = new Error('i am an error');
      });

      it('should display message if error occurs in next tick', function (done) {

        onResponse = function () {
          r.write('test');
          process.nextTick(function () {
            r.emit('error', err);
          });
        };

        s = requestIndex('/api/alert/', 'buffer');

        λ(s)
          .errors(function (e) {
            expect(e).toEqual(err);
            done();
          })
          .each(function (data) {
            expect(data.toString()).toEqual('test');
          });
      });
    });
  });
});
