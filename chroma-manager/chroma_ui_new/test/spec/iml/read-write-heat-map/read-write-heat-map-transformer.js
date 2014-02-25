describe('read write heat map transformer', function () {
  'use strict';

  var boundTransformer, stream, fixtures;

  beforeEach(module('readWriteHeatMap', 'dataFixtures'));

  beforeEach(inject(function (readWriteHeatMapTransformer, readWriteHeatMapDataFixtures) {
    stream = {
      type: 'stats_read_bytes'
    };
    boundTransformer = readWriteHeatMapTransformer.bind(stream);
    fixtures = _.cloneDeep(readWriteHeatMapDataFixtures);
  }));


  it('should throw if resp.body is not an object', function () {
    function shouldThrow() {
      boundTransformer({});
    }

    expect(shouldThrow).toThrow('readWriteHeatMapTransformer expects resp.body to be an object!');
  });

  it('should transform data', function () {
    fixtures.forEach(function (item) {
      var resp = boundTransformer({body: item.in});

      resp.body.forEach(function (item) {
        item.values.forEach(function (value) {
          value.x = value.x.toJSON();
        });
      });

      item.out.forEach(function (item) {
        item.values.forEach(function (value) {
          value.z = value.stats_read_bytes;
        });
      });

      expect(resp.body).toEqual(item.out);
    });
  });

  it('should transform data for writes', function () {
    stream.type = 'stats_write_bytes';

    fixtures.forEach(function (item) {
      var resp = boundTransformer({body: item.in});

      resp.body.forEach(function (item) {
        item.values.forEach(function (value) {
          value.x = value.x.toJSON();
        });
      });

      item.out.forEach(function (item) {
        item.values.forEach(function (value) {
          value.z = value.stats_write_bytes;
        });
      });

      expect(resp.body).toEqual(item.out);
    });
  });

  it('should normalize empty values to 0', function () {
    var resp = boundTransformer({
      body: {
        'fs-OST0000': [{
          data: {
            stats_write_bytes: 0
          },
          ts: '2014-02-28T23:15:32.350000+00:00',
          id: '3'
        }]
      }
    });

    expect(resp.body[0].values[0].z).toBe(0);
  });
});
