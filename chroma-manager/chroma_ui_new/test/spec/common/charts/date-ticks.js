describe('Date ticks', function () {
  'use strict';

  var moment, dateTicks, d3, start;

  beforeEach(module('charts'));

  beforeEach(inject(function (_moment_, _d3_, _dateTicks_) {
    moment = _moment_;
    d3 = _d3_;
    dateTicks = _dateTicks_;
    start = moment('2013-11-11 00:00');
  }));

  it('should format correctly for different months', function () {
    var func = dateTicks.getTickFormatFunc(start.twix('2013-12-11 00:00'));

    expect(func('2013-11-12 06:30')).toEqual('Nov 12 06:30');
  });

  it('should format correctly for different days', function () {
    var func = dateTicks.getTickFormatFunc(start.twix('2013-11-12 00:00'));

    expect(func('2013-11-11 01:30:00')).toEqual('11 01:30:00');
  });

  it('should format correctly for the same day', function () {
    var func = dateTicks.getTickFormatFunc(start.twix('2013-11-11 09:00'));

    expect(func('2013-11-11 08:30')).toEqual('08:30:00');
  });

  it('should accept an array as a range', function () {
    var func = dateTicks.getTickFormatFunc(['2013-11-11 00:00', '2013-12-11 00:00']);

    expect(func('2013-11-12 13:30')).toEqual('Nov 12 13:30');
  });
});
