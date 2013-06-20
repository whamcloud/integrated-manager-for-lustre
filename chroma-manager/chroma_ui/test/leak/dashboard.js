describe('dashboard', function () {
  'use strict';

  var chartManager;

  beforeEach(function beforeEachDashboard() {
    var callCount = 2;

    window.STATIC_URL = 'foo';
    window.TIME_OFFSET = -2;
    window.Api = {
      get: jasmine.createSpy('Api.get').andCallFake(function () {
        var callback = arguments[2];

        function generateData(times) {
          return window.lodash.range(times).map(function () {
            var date = new Date();
            date.setUTCMinutes(date.getUTCMinutes() - (2 * times));

            return {
              data: {
                stats_read_bytes: window.lodash.random(30000000000, 40000000000),
                stats_write_bytes: window.lodash.random(30000000000, 40000000000)
              },
              ts: date.toISOString().replace(/\.\d{3}Z/, '+00:00')
            };
          });

        }

        callback(generateData(callCount));
        callCount -= 1;
      })
    };

    $('body').append('<div class="chart" id="server_read_write"></div>');
    $.fn.button = angular.noop;
  });

  afterEach(function afterEachDashboard() {
    chartManager.destroy();
    $('.chart').remove();
    $('.magni').remove();

    delete window.STATIC_URL;
    delete window.TIME_OFFSET;
    delete window.Api;
    delete $.fn.button;
  });

  it('should not build up StackIndex instances', function () {
    chartManager = window.ChartManager({
      chart_group: 'dashboard',
      default_time_boundary: 1000,
      interval_seconds: 10
    });


    chartManager.add_chart('readwrite', 'dashboard', {
      url: function () { return 'target/metric/'; },
      api_params: { reduce_fn: 'sum', kind: 'OST'},
      api_params_callback: function (api_params) { api_params.host_id = 1; return api_params; },
      metrics: ['stats_read_bytes', 'stats_write_bytes'],
      chart_config: {
        chart: { renderTo: 'server_read_write'},
        title: { text: 'Read/Write bandwidth'},
        xAxis: { type: 'datetime'},
        yAxis: [{
          title: null,
          labels: {formatter: angular.noop}
        }],
        series: [
          { type: 'area', name: 'read' },
          { type: 'area', name: 'write' }
        ]
      }
    });

    function getStackSize() {
      return Object.keys(chartManager.config.charts.dashboard.readwrite.instance.yAxis[0].stacks.area).length;
    }

    chartManager.render_charts();
    var startStackSize = getStackSize();
    chartManager.render_charts();
    var endStackSize = getStackSize();

    expect(startStackSize).toEqual(endStackSize);
  });
});
