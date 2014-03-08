describe('splice old data transformer', function () {
  'use strict';

  var spliceOldDataTransformer, stream, data, date;

  beforeEach(module('charts'));

  mock.beforeEach(function () {
    var moment = jasmine.createSpy('moment').andReturn({
      subtract: jasmine.createSpy('subtract').andCallFake(function () {
        return date;
      })
    });

    return {
      name: 'moment',
      value: moment
    };
  });

  beforeEach(inject(function (_spliceOldDataTransformer_) {
    spliceOldDataTransformer = _spliceOldDataTransformer_;

    data = [];

    stream = {
      size: 5,
      unit: 'minutes',
      getter: jasmine.createSpy('getter').andCallFake(function () {
        return data;
      })
    };
  }));

  it('should throw if unit is not passed', function () {
    expect(shouldThrow).toThrow('Stream.unit is required for the spliceOldDataTransfomer!');

    function shouldThrow () {
      delete stream.unit;

      spliceOldDataTransformer.call(stream);
    }
  });

  it('should throw if size is not passed', function () {
    expect(shouldThrow).toThrow('Stream.size is required for the spliceOldDataTransfomer!');

    function shouldThrow () {
      delete stream.size;

      spliceOldDataTransformer.call(stream);
    }
  });

  it('should throw if data is not an array', function () {
    expect(shouldThrow).toThrow('Data not in expected format for spliceOldDataTransformer!');

    function shouldThrow () {
      data = {};

      spliceOldDataTransformer.call(stream);
    }
  });

  it('should remove old data values', function () {
    data = [
      {
        values: [
          {x: new Date('12/10/2013')}
        ]
      }
    ];

    date = new Date('12/11/2013');

    spliceOldDataTransformer.call(stream, {});

    expect(data[0].values.length).toBe(0);
  });

  it('should keep newer data values', function () {
    data = [
      {
        values: [
          {x: new Date('12/11/2013')}
        ]
      }
    ];

    date = new Date('12/10/2013');

    spliceOldDataTransformer.call(stream, {});

    expect(data[0].values).toEqual([{x: new Date('12/11/2013')}]);
  });

  it('should remove all old values', function () {
    data = [
      {
        values: [
          {x: new Date('12/10/2013')},
          {x: new Date('12/10/2013 23:59:59')},
          {x: new Date('12/11/2013')}
        ]
      }
    ];

    date = new Date('12/11/2013');

    spliceOldDataTransformer.call(stream, {});

    expect(data[0].values).toEqual([{x: new Date('12/11/2013')}]);
  });
});