'use strict';

var metricsModelFactory = require('../../../models/metrics-model').metricsModelFactory,
  sinon = require('sinon');

require('jasmine-sinon');

describe('Metrics Model', function () {
  var name, dataSourceFactory, dataSource, metricsModel, primus, logger, metrics, spark;

  beforeEach(function () {
    name = 'metricsChannel';

    metrics = {
      on: sinon.spy()
    };

    primus = {
      channel: sinon.stub().returns(metrics)
    };

    logger = {
      info: sinon.spy(),
      error: sinon.spy()
    };

    spark = {
      write: sinon.spy(),
      on: sinon.spy()
    };

    dataSource = {
      start: sinon.spy(),
      stop: sinon.spy(),
      on: sinon.spy(),
      removeListener: sinon.spy()

    };

    dataSourceFactory = sinon.stub().returns(dataSource);

    metricsModel = metricsModelFactory(primus, logger);
  });

  it('should throw if no args are passed', function () {
    expect(function () {metricsModel(); }).toThrow();
  });

  it('should throw if channelName is not passed', function () {
    expect(function () {metricsModel(null, function () {}); }).toThrow();
  });

  it('should throw if dataSourceFactory is not passed', function () {
    expect(function () {metricsModel(name, null); }).toThrow();
  });

  describe('starting', function () {
    beforeEach(function () {
      metricsModel(name, dataSourceFactory);
    });

    it('should open a channel from the channelName', function () {
      expect(primus.channel).toHaveBeenCalledWithExactly(name);
    });

    it('should setup connection handling', function () {
      expect(metrics.on).toHaveBeenCalledWith('connection', sinon.match.func);
    });

    describe('when a connection occurs', function () {
      beforeEach(function () {
        metrics.on.callArgWith(1, spark);
      });

      it('should log the connection', function () {
        expect(logger.info).toHaveBeenCalledOnce();
      });

      it('should call the dataSourceFactory with the channel name', function () {
        expect(dataSourceFactory).toHaveBeenCalledWithExactly(name);
      });

      it('should register a data listener on the datasource on event', function () {
        expect(dataSource.on).toHaveBeenCalledWithExactly('data', sinon.match.func);
      });

      it('should register an error listener on the datasource error event', function () {
        expect(dataSource.on).toHaveBeenCalledWithExactly('error', sinon.match.func);
      });

      it('should register a data listener on the spark', function () {
        expect(spark.on).toHaveBeenCalledWithExactly('data', sinon.match.func);
      });

      it('should register an end listener on the spark', function () {
        expect(spark.on).toHaveBeenCalledWithExactly('end', sinon.match.func);
      });

      describe('when data is sent from the datasource', function () {
        var data;
        beforeEach(function () {
          data = {
            data: [
              {foo: 'bar'}
            ]
          };

          dataSource.on.withArgs('data', sinon.match.func).callArgWith(1, data);
        });

        it('should log that data was sent', function () {
          expect(logger.info).toHaveBeenCalledTwice();
        });

        it('should write to the spark', function () {
          expect(spark.write).toHaveBeenCalledWithExactly(data);
        });
      });

      describe('when an error is sent from the datasource', function () {
        var error;

        beforeEach(function () {
          error = new Error('uh oh');

          dataSource.on.withArgs('error', sinon.match.func).callArgWith(1, error);
        });

        it('should log that an error was sent', function () {
          expect(logger.error).toHaveBeenCalledOnce();
        });

        it('should write to the spark', function () {
          expect(spark.write).toHaveBeenCalledWithExactly(error);
        });
      });

      describe('when data is sent from the spark', function () {
        var onData;

        beforeEach(function () {
          onData = spark.on.withArgs('data', sinon.match.func);
        });

        it('should write an error if options are not supplied', function () {
          onData.callArgWith(1, null);

          expect(spark.write).toHaveBeenCalledWithExactly({
            error: 'options.query not supplied to metricsModel!'
          });
        });

        it('should write an error if query is not supplied', function () {
          onData.callArgWith(1, {});

          expect(spark.write).toHaveBeenCalledWithExactly({
            error: 'options.query not supplied to metricsModel!'
          });
        });

        it('should log a query was sent', function () {
          onData.callArgWith(1, {query: {}});

          expect(logger.info).toHaveBeenCalledTwice();
        });

        it('should start the data source', function () {
          var options = {query: {foo: 'bar'}};

          onData.callArgWith(1, options);

          expect(dataSource.start).toHaveBeenCalledWithExactly(options);
        });
      });

      describe('when the spark is ended', function () {
        beforeEach(function () {
          spark.on.withArgs('end', sinon.match.func).callArg(1);
        });

        it('should log it', function () {
          expect(logger.info).toHaveBeenCalledTwice();
        });

        it('should stop the datasource', function () {
          expect(dataSource.stop).toHaveBeenCalledOnce();
        });

        it('should remove the data listener from the datasource', function () {
          expect(dataSource.removeListener).toHaveBeenCalledWithExactly('data', sinon.match.func);
        });

        it('should remove the error listener from the datasource', function () {
          expect(dataSource.removeListener).toHaveBeenCalledWithExactly('error', sinon.match.func);
        });
      });
    });
  });
});