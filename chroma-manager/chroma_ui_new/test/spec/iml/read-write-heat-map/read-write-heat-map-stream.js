describe('read write heat map stream', function () {
  'use strict';

  var ReadWriteHeatMapStream, stream, readWriteHeatMapTransformer, replaceTransformer;

  beforeEach(module('readWriteHeatMap'));

  mock.beforeEach('stream');

  beforeEach(inject(function (_ReadWriteHeatMapStream_, _stream_, _readWriteHeatMapTransformer_, _replaceTransformer_) {
    ReadWriteHeatMapStream = _ReadWriteHeatMapStream_;
    stream = _stream_;
    readWriteHeatMapTransformer = _readWriteHeatMapTransformer_;
    replaceTransformer = _replaceTransformer_;
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
  });
});