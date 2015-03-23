'use strict';

var saveTgzThenModule = require('../../lib/save-tgz-then').wiretree;
var Promise = require('promise');
var stream = require('stream');

describe('save TGZ module', function () {
  var saveTgzThen, requests, zlib, tar, streams, promise;

  beforeEach(function () {
    streams = {};

    streams.requestPipeStream = new stream.Readable();
    streams.requestPipeStream._read = function _read () {};
    streams.requestPipeStream.resume();
    requests = {
      requestPipe: jasmine.createSpy('requestPipe').and.returnValue(streams.requestPipeStream)
    };

    streams.gunzipStream = new stream.PassThrough();
    streams.gunzipStream.resume();
    zlib = {
      createGunzip: jasmine.createSpy('createGunzip').and.returnValue(streams.gunzipStream)
    };

    streams.extractStream = new stream.PassThrough();
    streams.extractStream.resume();
    tar = {
      Extract: jasmine.createSpy('Extract').and.returnValue(streams.extractStream)
    };

    saveTgzThen = saveTgzThenModule(Promise, requests, zlib, tar);
    promise = saveTgzThen('https://registry.npmjs.org/foo/-/foo-1.0.0.tgz', {});
  });

  it('should return a Promise', function () {
    expect(promise).toEqual(jasmine.any(Promise));
  });

  it('should request the tgz path', function () {
    expect(requests.requestPipe).toHaveBeenCalledWith('https://registry.npmjs.org/foo/-/foo-1.0.0.tgz');
  });

  it('should create a gunzip stream', function () {
    expect(zlib.createGunzip).toHaveBeenCalled();
  });

  it('should create an extract stream', function () {
    expect(tar.Extract).toHaveBeenCalledWith({});
  });

  ['requestPipeStream', 'gunzipStream', 'extractStream'].forEach(function iterate (name) {
    pit('should reject on ' + name + ' error', function () {
      var error = new Error('oh noes!');

      streams[name].emit('error', error);

      return promise.catch(function assertError (err) {
        expect(err).toBe(error);
      });
    });
  });

  pit('should resolve when stream has finished', function () {
    streams.requestPipeStream.push('beep');
    streams.requestPipeStream.push(null);

    //Simply returning this will assert the promise has resolved.
    return promise;
  });
});
