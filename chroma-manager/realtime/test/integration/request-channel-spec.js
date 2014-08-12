'use strict';

var getClient = require('./util/get-client');

describe('request channel', function () {
  var client, spark;

  beforeEach(function () {
    client = getClient();

    spark = client.channel('request');
  });

  afterEach(function () {
    spark.end();
    client.end();
  });

  it('should ack an error if data is not an object', function (done) {
    spark.send('req', [], function (data) {
      expect(data).toEqual({
        statusCode: 400,
        error: {
          message: 'instance is not of a type(s) object\ninstance.path is required\n',
          name: 'Error',
          stack: jasmine.any(String)
        }
      });
      done();
    });
  });

  it('should ack an error if path is missing', function (done) {
    spark.send('req', {}, function (data) {
      expect(data).toEqual({
        statusCode: 400,
        error: {
          message: 'instance.path is required\n',
          name: 'Error',
          stack: jasmine.any(String)
        }
      });
      done();
    });
  });

  it('should ack an error if method is wrong', function (done) {
    spark.send('req', { path: '/host', options: { method: 'got' } }, function (data) {
      expect(data).toEqual({
        statusCode: 400,
        error: {
          message: 'instance.options.method is not one of enum values: get,post,put,patch,delete\n',
          name: 'Error',
          stack: jasmine.any(String)
        }
      });
      done();
    });
  });

  it('should return an error if data is not an object', function (done) {
    spark.on('data', function (data) {
      expect(data).toEqual({
        statusCode: 400,
        error: {
          message: 'instance is not of a type(s) object\ninstance.path is required\n',
          name: 'Error',
          stack: jasmine.any(String)
        }
      });
      done();
    });

    spark.send('req', []);
  });

  it('should return an error if path is missing', function (done) {
    spark.on('data', function (data) {
      expect(data).toEqual({
        statusCode: 400,
        error: {
          message: 'instance.path is required\n',
          name: 'Error',
          stack: jasmine.any(String)
        }
      });
      done();
    });

    spark.send('req', {});
  });

  it('should return an error if path is missing', function (done) {
    spark.on('data', function (data) {
      expect(data).toEqual({
        statusCode: 400,
        error: {
          message: 'instance.options.method is not one of enum values: get,post,put,patch,delete\n',
          name: 'Error',
          stack: jasmine.any(String)
        }
      });
      done();
    });

    spark.send('req', { path: '/host', options: { method: 'got' } });
  });

  it('should ack a response to a known endpoint', function (done) {
    spark.send('req', { path: '/host'}, function (data) {
      expect(data).toEqual({
        statusCode: 200,
        body: jasmine.any(Object)
      });
      done();
    });
  });

  it('should respond to a known endpoint', function (done) {
    spark.on('data', function (data) {
      expect(data).toEqual({
        statusCode: 200,
        body: jasmine.any(Object)
      });
      done();
    });

    spark.send('req', { path: '/host'});
  });

  it('should error on an unknown endpoint', function (done) {
    spark.on('data', function (data) {
      expect(data).toEqual({
        statusCode: 404,
        error: jasmine.any(Object)
      });
      done();
    });

    spark.send('req', { path: '/foobar'});
  });
});
