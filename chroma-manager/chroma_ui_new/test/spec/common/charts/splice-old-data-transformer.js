describe('splice old data transformer', function () {
  'use strict';

  beforeEach(module('charts', function ($provide) {
    $provide.value('getServerMoment', jasmine.createSpy('getServerMoment').andReturn({
      subtract: jasmine.createSpy('subtract')
    }));
  }));

  var spliceOldDataTransformer, getServerMoment, moment, stream;

  beforeEach(inject(function (_spliceOldDataTransformer_, _getServerMoment_, _moment_) {
    spliceOldDataTransformer = _spliceOldDataTransformer_;
    getServerMoment = _getServerMoment_;
    moment = _moment_;

    stream = {
      size: 5,
      unit: 'minutes',
      getter: jasmine.createSpy('getter')
    };
  }));

  it('should throw if unit is not passed', function () {
    stream.getter.andReturn([]);

    expect(shouldThrow).toThrow('Stream.unit is required for the spliceOldDataTransfomer!');

    function shouldThrow () {
      delete stream.unit;

      spliceOldDataTransformer.call(stream);
    }
  });

  it('should throw if size is not passed', function () {
    stream.getter.andReturn([]);

    expect(shouldThrow).toThrow('Stream.size is required for the spliceOldDataTransfomer!');

    function shouldThrow () {
      delete stream.size;

      spliceOldDataTransformer.call(stream);
    }
  });

  it('should throw if data is not an array', function () {
    expect(shouldThrow).toThrow('Data not in expected format for spliceOldDataTransformer!');

    function shouldThrow () {
      stream.getter.andReturn({});

      spliceOldDataTransformer.call(stream);
    }
  });

  it('should remove old data values', function () {
    var data = [
      {
        values: [
          { x: new Date('12/10/2013') }
        ]
      }
    ];

    stream.getter.andReturn(data);

    getServerMoment.plan().subtract.andReturn(moment('2013-12-11 00:00'));

    spliceOldDataTransformer.call(stream, {});

    expect(data).toEqual([]);
  });

  it('should keep newer data values', function () {
    var data = [
      {
        values: [
          { x: new Date('12/11/2013') }
        ]
      }
    ];

    stream.getter.andReturn(data);

    getServerMoment.plan().subtract.andReturn(moment('2013-12-10 00:00'));

    spliceOldDataTransformer.call(stream, {});

    expect(data[0].values).toEqual([{ x: new Date('12/11/2013') }]);
  });

  it('should remove all old values', function () {
    var data = [
      {
        values: [
          { x: new Date('12/10/2013') },
          { x: new Date('12/10/2013 23:59:59') },
          { x: new Date('12/11/2013') }
        ]
      }
    ];

    stream.getter.andReturn(data);

    getServerMoment.plan().subtract.andReturn(moment('2013-12-11 00:00'));

    spliceOldDataTransformer.call(stream, {});

    expect(data[0].values).toEqual([{ x: new Date('12/11/2013') }]);
  });

  it('should splice empty series', function () {
    var emptySeries = [
      { key: 'close', values: [{ x: new Date('12/11/2013') }] },
      { key: 'getattr', values: [{ x: new Date('12/10/2013') }] },
      { key: 'getxattr', values: [{ x: new Date('12/11/2013') }] },
      { key: 'link', values: [] },
      { key: 'mkdir', values: [] },
      { key: 'mknod', values: [{ x: new Date('12/10/2013 23:59:59') }] },
      { key: 'open', values: [] },
      { key: 'rename', values: [{ x: new Date('12/11/2013') }] },
      { key: 'rmdir', values: [] },
      { key: 'setattr', values: [] },
      { key: 'statfs', values: [{ x: new Date('12/11/2013') }] },
      { key: 'unlink', values: [] }
    ];

    stream.getter.andReturn(emptySeries);

    getServerMoment.plan().subtract.andReturn(moment('2013-12-11 00:00'));

    spliceOldDataTransformer.call(stream, {});

    expect(emptySeries).toEqual([
      { key: 'close', values: [{ x: new Date('12/11/2013') }] },
      { key: 'getxattr', values: [{ x: new Date('12/11/2013') }] },
      { key: 'rename', values: [{ x: new Date('12/11/2013') }] },
      { key: 'statfs', values: [{ x: new Date('12/11/2013') }] }
    ]);
  });
});
