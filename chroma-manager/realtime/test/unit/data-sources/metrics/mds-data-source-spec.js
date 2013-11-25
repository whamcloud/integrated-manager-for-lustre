'use strict';

var sinon = require('sinon'),
  mdsDataSourceFactory = require('../../../../data-sources/metrics/mds-data-source');

require('jasmine-sinon');

describe('Mds data source', function () {
  var mdsDataSource, MetricsDataSource, name;

  beforeEach(function () {
    name = 'fooChannel';

    MetricsDataSource = function () {
      this.url = 'foo/';
    };

    sinon.spy(MetricsDataSource, 'call');

    MetricsDataSource.prototype = {
      beforeSend: {
        call: sinon.mock().returnsArg(1)
      }
    };

    mdsDataSource = mdsDataSourceFactory(MetricsDataSource)(name);
  });

  it('should call the MetricsDataSource', function () {
    expect(MetricsDataSource.call).toHaveBeenCalledWithExactly(mdsDataSource, name);
  });

  it('should call the metricsDataSource before send', function () {
    mdsDataSource.beforeSend({});

    expect(MetricsDataSource.prototype.beforeSend.call)
      .toHaveBeenCalledWithExactly(mdsDataSource, {});
  });

  it('should extend the options', function () {
    var result = mdsDataSource.beforeSend({});

    expect(result).toEqual({
      url : 'foo/host/metric/',
      qs : {
        reduce_fn : 'average',
        role : 'MDS',
        metrics : 'cpu_total,cpu_user,cpu_system,cpu_iowait,mem_MemFree,mem_MemTotal'
      }
    });
  });
});