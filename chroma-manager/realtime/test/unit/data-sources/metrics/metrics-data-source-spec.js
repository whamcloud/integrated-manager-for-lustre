'use strict';

var getMetricsDataSource = require('../../../../data-sources/metrics/metrics-data-source'),
  sinon = require('sinon');

require('jasmine-sinon');

describe('Metrics data source', function () {
  var BaseDataSource, metricsDataSource, name, clock, request, logger, conf;

  beforeEach(function () {
    name = 'fooChannel';
    request = logger = conf = {};

    clock = sinon.useFakeTimers(1330688329321);

    BaseDataSource = sinon.spy();

    sinon.stub(BaseDataSource, 'call', function (context) {
      context.logger = {info: sinon.stub()};
    });

    var MetricsDataSource = getMetricsDataSource(conf, request, logger, BaseDataSource);

    metricsDataSource = new MetricsDataSource(name);
  });

  afterEach(function () {
    BaseDataSource.call.restore();
    clock.restore();
  });

  it('should call the BaseDataSource', function () {
    expect(BaseDataSource.call).toHaveBeenCalledWithExactly(metricsDataSource, conf, request, logger, name);
  });

  it('should log the query before sending', function () {
    metricsDataSource.beforeSend({query: {}});

    expect(metricsDataSource.logger.info).toHaveBeenCalledOnce();
  });

  it('should process the options before sending', function () {
    var result = metricsDataSource.beforeSend({query: {}});

    expect(result).toEqual({qs: {}});
  });

  it('should calculate a date range in the options before sending', function () {
    var result = metricsDataSource.beforeSend({query: {
      unit: 'minutes',
      size: 10
    }});

    expect(result).toEqual({
      qs: {
        end: '2012-03-02T11:38:49.321Z',
        begin: '2012-03-02T11:28:49.321Z'
      }
    });
  });
});