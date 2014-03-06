describe('read write heat map transformer', function () {
  'use strict';

  var $q, $rootScope, boundTransformer, deferred, stream, fixtures;

  beforeEach(module('readWriteHeatMap', 'dataFixtures'));

  beforeEach(inject(function (readWriteHeatMapTransformer, _$rootScope_, _$q_, readWriteHeatMapDataFixtures) {
    stream = {
      type: 'stats_read_bytes'
    };
    $q = _$q_;
    $rootScope = _$rootScope_;
    boundTransformer = readWriteHeatMapTransformer.bind(stream);
    deferred = $q.defer();
    fixtures = _.cloneDeep(readWriteHeatMapDataFixtures);
  }));


  it('should throw if resp.body is not an object', function () {
    function shouldThrow() {
      boundTransformer({}, deferred);
    }

    expect(shouldThrow).toThrow('readWriteHeatMapTransformer expects resp.body to be an object!');
  });

  it('should transform data', function () {
    fixtures.forEach(function (item) {
      var deferred = $q.defer();

      boundTransformer({body: item.in}, deferred);

      deferred.promise.then(function (resp) {
        var data = resp.body;

        data.forEach(function (item) {
          item.values.forEach(function (value) {
            value.x = value.x.toJSON();
          });
        });

        item.out.forEach(function (item) {
          item.values.forEach(function (value) {
            value.z = value.stats_read_bytes;
          });
        });

        expect(data).toEqual(item.out);
      });

      $rootScope.$digest();
    });
  });

  it('should transform data for writes', function () {
    stream.type = 'stats_write_bytes';

    fixtures.forEach(function (item) {
      var deferred = $q.defer();

      boundTransformer({body: item.in}, deferred);

      deferred.promise.then(function (resp) {
        var data = resp.body;

        data.forEach(function (item) {
          item.values.forEach(function (value) {
            value.x = value.x.toJSON();
          });
        });

        item.out.forEach(function (item) {
          item.values.forEach(function (value) {
            value.z = value.stats_write_bytes;
          });
        });

        expect(data).toEqual(item.out);
      });

      $rootScope.$digest();
    });
  });

  it('should normalize empty values to 0', function () {
    var deferred = $q.defer();

    boundTransformer({
      body: {
        'fs-OST0000': [{
          data: {
            stats_write_bytes: 0
          },
          ts: '2014-02-28T23:15:32.350000+00:00',
          id: '3'
        }]
      }
    }, deferred);

    deferred.promise.then(function (resp) {
      var data = resp.body;

      expect(data[0].values[0].z).toBe(0);
    });

    $rootScope.$digest();
  });
});