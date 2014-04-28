describe('read write heat map stream', function () {
  'use strict';

  beforeEach(module('readWriteHeatMap', function ($provide) {
    $provide.value('stream', jasmine.createSpy('stream').andCallFake(function () {
      return function ReadWriteHeatMapStream () {
        this.getter = jasmine.createSpy('getter');
      };
    }));
  }, {
    replaceTransformer: jasmine.createSpy('replaceTransformer'),
    readWriteHeatMapTransformer: jasmine.createSpy('readWriteHeatMapTransformer'),
    beforeStreamingDuration: jasmine.createSpy('beforeStreamingDuration')
  }));

  var ReadWriteHeatMapStream, stream, readWriteHeatMapTransformer, replaceTransformer, beforeStreamingDuration;

  beforeEach(inject(function (_ReadWriteHeatMapStream_, _stream_, _readWriteHeatMapTransformer_, _replaceTransformer_,
                              _beforeStreamingDuration_) {
    ReadWriteHeatMapStream = _ReadWriteHeatMapStream_;
    stream = _stream_;
    readWriteHeatMapTransformer = _readWriteHeatMapTransformer_;
    replaceTransformer = _replaceTransformer_;
    beforeStreamingDuration = _beforeStreamingDuration_;
  }));

  it('should create a stream to retrieve ost read write metrics and process them', function () {
    var config = {
      params: {
        qs: {
          kind: 'OST',
          metrics: 'stats_read_bytes,stats_write_bytes',
          num_points: '20'
        }
      },
      transformers: [readWriteHeatMapTransformer, replaceTransformer]
    };

    expect(stream).toHaveBeenCalledWith('targetostmetrics', 'httpGetOstMetrics', config);
  });

  it('should setup before streaming for duration', function () {
    expect(ReadWriteHeatMapStream.prototype.beforeStreaming).toBe(beforeStreamingDuration);
  });

  describe('use', function () {
    var readWriteHeatMapStream;

    beforeEach(function () {
      readWriteHeatMapStream = new ReadWriteHeatMapStream();
    });

    it('should validate the type when setting it', function () {
      function shouldThrow () {
        readWriteHeatMapStream.type = 'notatype';
      }

      expect(shouldThrow).toThrow('Type: notatype is not a valid type!');
    });

    it('should retrieve a set type', function () {
      var value = 'stats_read_bytes';

      readWriteHeatMapStream.type = value;

      expect(readWriteHeatMapStream.type).toEqual(value);
    });

    it('should switch the type', function () {
      var data = [
        {
          values: [
            {
              stats_read_bytes: 20,
              stats_write_bytes: 10,
              z: 20
            }
          ]
        }
      ];

      readWriteHeatMapStream.getter.andReturn(data);

      readWriteHeatMapStream.switchType('stats_write_bytes');

      expect(data[0].values[0].z).toBe(10);
    });
  });
});