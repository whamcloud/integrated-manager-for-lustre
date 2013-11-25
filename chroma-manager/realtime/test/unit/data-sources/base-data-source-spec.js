'use strict';

var BaseDataSource = require('../../../data-sources/base-data-source'),
  sinon = require('sinon');

require('jasmine-sinon');

describe('data source', function () {
  var clock, baseDataSource, name, request, logger, conf;

  beforeEach(function () {
    clock = sinon.useFakeTimers();

    conf = {
      apiUrl: 'https://a/b/c'
    };

    request = {
      get: sinon.stub()
    };

    logger = {
      child: sinon.stub().returns({
        info: sinon.stub()
      })
    };

    name = 'fooChannel';

    baseDataSource = new BaseDataSource(conf, request, logger, name);
  });

  afterEach(function () {
    clock.restore();
    baseDataSource.removeAllListeners();
  });

  it('should create a child logger based on the name', function () {
    expect(logger.child.calledWithExactly({channelName: name})).toBeTruthy();
  });

  it('should get new data before polling', function () {
    baseDataSource.start({});

    expect(request.get).toHaveBeenCalledOnce();
  });

  it('should get new data after 10 seconds', function () {
    baseDataSource.start({});

    clock.tick(10000);

    expect(request.get).toHaveBeenCalledTwice();
  });

  it('should emit data', function (done) {
    var body = [];

    request.get.callsArgWith(1, null, {statusCode: 200}, body);

    baseDataSource.on('data', function callback(data) {
      expect(data).toEqual({data: body});

      done();
    });

    baseDataSource.start({});
  });

  it('should emit errors on resps >= 400', function (done) {
    var body = [];

    request.get.callsArgWith(1, null, {statusCode: 400}, body);

    baseDataSource.on('error', function callback(err) {
      expect(err).toEqual({status: 400, error: body});

      done();
    });

    baseDataSource.start({});
  });

  it('should emit an error object', function (done) {
    var error = new Error('foo');

    request.get.callsArgWith(1, error, {statusCode: 500}, undefined);

    baseDataSource.on('error', function callback(err) {
      expect(err).toEqual({error: error});

      done();
    });

    baseDataSource.start({});
  });

  it('should stop polling', function () {
    baseDataSource.start({});

    baseDataSource.stop();

    clock.tick(1000);

    expect(request.get.calledOnce).toBeTruthy();
  });
});