describe('Date ticks', function () {
  'use strict';

  var moment, dateTicks, d3, start;

  beforeEach(module('charts'));

  beforeEach(inject(function (_moment_, _d3_, _dateTicks_) {
    moment = _moment_;
    d3 = _d3_;
    dateTicks = _dateTicks_;
    start = moment('11/11/2013 00:00:00');
  }));

  it('should format correctly for different months', function () {
    var func = dateTicks.getTickFormatFunc(start.twix('12/11/2013 00:00:00'));

    expect(func('11/12/2013 06:30:00')).toEqual('Nov 12 06:30');
  });

  it('should format correctly for different days', function () {
    var func = dateTicks.getTickFormatFunc(start.twix('11/12/2013 00:00:00'));

    expect(func('11/11/2013 01:30:00')).toEqual('11 01:30:00');
  });

  it('should format correctly for the same day', function () {
    var func = dateTicks.getTickFormatFunc(start.twix('11/11/2013 09:00:00'));

    expect(func('11/11/2013 08:30:00')).toEqual('08:30:00');
  });

  it('should accept an array as a range', function () {
    var func = dateTicks.getTickFormatFunc(['11/11/2013 00:00:00', '12/11/2013 00:00:00']);

    expect(func('11/12/2013 13:30:00')).toEqual('Nov 12 13:30');
  });
});
