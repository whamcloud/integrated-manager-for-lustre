'use strict';

var sinon = require('sinon'),
  mdtDataSourceFactory = require('../../../../data-sources/metrics/mdt-data-source');

require('jasmine-sinon');

describe('Mdt data source', function () {
  var mdtDataSource, MetricsDataSource, name;

  beforeEach(function () {
    name = 'fooChannel';

    MetricsDataSource = function () {
      this.url = 'https://a/b/c/';
    };

    sinon.spy(MetricsDataSource, 'call');

    MetricsDataSource.prototype = {
      beforeSend: {
        call: sinon.mock().returnsArg(1)
      }
    };

    mdtDataSource = mdtDataSourceFactory(MetricsDataSource)(name);
  });

  it('should call the MetricsDataSource', function () {
    expect(MetricsDataSource.call).toHaveBeenCalledWithExactly(mdtDataSource, name);
  });

  it('should call the metricsDataSource before send', function () {
    mdtDataSource.beforeSend({});

    expect(MetricsDataSource.prototype.beforeSend.call)
      .toHaveBeenCalledWithExactly(mdtDataSource, {});
  });

  it('should extend the options', function () {
    var result = mdtDataSource.beforeSend({});

    expect(result).toEqual({
      url : 'https://a/b/c/target/metric/',
      qs : {
        reduce_fn : 'sum',
        kind : 'MDT',
        metrics : 'stats_close,stats_getattr,stats_getxattr,stats_link,stats_mkdir,stats_mknod,stats_open,\
stats_rename,stats_rmdir,stats_setattr,stats_statfs,stats_unlink'
      }
    });
  });

});