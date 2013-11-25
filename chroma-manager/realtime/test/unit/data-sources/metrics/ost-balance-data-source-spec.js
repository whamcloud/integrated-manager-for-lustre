'use strict';

var sinon = require('sinon'),
  ostBalanceDataSourceFactory = require('../../../../data-sources/metrics/ost-balance-data-source');

require('jasmine-sinon');

describe('Ost balance data source', function () {
  var ostBalanceDataSource, BaseDataSource, name, conf, request, logger;

  beforeEach(function () {
    name = 'fooChannel';

    BaseDataSource = function () {
      this.url = 'https://a/b/c/';
      this.logger = {
        info: sinon.spy()
      };
      this.request = sinon.mock();
      this.emit = sinon.mock();
    };

    conf = request = logger = {};

    sinon.spy(BaseDataSource, 'call');

    ostBalanceDataSource = ostBalanceDataSourceFactory(conf, request, logger, BaseDataSource)(name);
  });

  it('should call the BaseDataSource', function () {
    expect(BaseDataSource.call).toHaveBeenCalledWithExactly(ostBalanceDataSource, conf, request, logger, name);
  });

  it('should extend the query', function () {
    var result = ostBalanceDataSource.beforeSend({query: {}});

    expect(result).toEqual({
      url : 'https://a/b/c/target/metric/',
      qs : {
        kind : 'OST',
        metrics : 'kbytestotal,kbytesfree',
        latest : true
      }
    });
  });

  it('should include the percentage if it is passed in', function () {
    var result = ostBalanceDataSource.beforeSend({query: {percentage: 25}});

    expect(result).toEqual({
      url : 'https://a/b/c/target/metric/',
      qs : {
        kind : 'OST',
        metrics : 'kbytestotal,kbytesfree',
        latest : true,
        percentage: 25
      }
    });
  });

  it('should log the query', function () {
    ostBalanceDataSource.beforeSend({query: {}});

    expect(ostBalanceDataSource.logger.info).toHaveBeenCalledOnce();
  });


  it('should transform results with fetched filesystem data', function () {
    ostBalanceDataSource.transformData({}, function () {});

    expect(ostBalanceDataSource.request).toHaveBeenCalledWith({
      url: 'https://a/b/c/target/',
      qs: {
        kind: 'OST',
        limit: 0
      }
    });
  });

  it('should emit an error if filesystem request return an error', function () {
    var err = new Error('foo');

    ostBalanceDataSource.transformData({}, function () {});

    ostBalanceDataSource.request.callArgWith(1, err, {}, []);

    expect(ostBalanceDataSource.emit).toHaveBeenCalledWithExactly('error', {error: err});
  });

  it('should emit an error if statusCode is >= 400', function () {
    ostBalanceDataSource.transformData({}, function () {});

    ostBalanceDataSource.request.callArgWith(1, null, {statusCode: 400}, []);

    expect(ostBalanceDataSource.emit).toHaveBeenCalledWithExactly('error', {statusCode: 400, error: []});
  });

  it('should call the done callback with transformed data', function (done) {
    ostBalanceDataSource.transformData({
      23: [{fooz: 'bar'}]
    }, callback);

    ostBalanceDataSource.request.callArgWith(1, null, {}, {objects: [{id: '23', name: 'baz'}]});

    function callback (data) {
      expect(data).toEqual({'baz': [{fooz: 'bar'}]});
      done();
    }
  });

  it('should call the done callback unchanged if target does not exist', function (done) {
    ostBalanceDataSource.transformData({
      23: [{fooz: 'bar'}]
    }, callback);

    ostBalanceDataSource.request.callArgWith(1, null, {}, {objects: [{id: '24', name: 'baz'}]});

    function callback (data) {
      expect(data).toEqual({23: [{fooz: 'bar'}]});
      done();
    }
  });
});