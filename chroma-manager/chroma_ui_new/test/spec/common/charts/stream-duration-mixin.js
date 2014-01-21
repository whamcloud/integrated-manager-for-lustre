describe('stream duration mixin', function () {
  'use strict';

  beforeEach(module('charts'));

  var streamDurationMixin, data, cb, params;

  beforeEach(inject(function (_streamDurationMixin_) {
    streamDurationMixin = _streamDurationMixin_;

    data = [];

    params = {
      qs: {}
    };

    cb = jasmine.createSpy('callback');

    streamDurationMixin.updateParams = jasmine.createSpy('updateParams');
    streamDurationMixin.getter = jasmine.createSpy('getter').andCallFake(function () {
      return data;
    });
  }));

  describe('duration change', function () {
    beforeEach(function () {
      streamDurationMixin.setDuration(5, 'minutes');
    });

    it('should update params on duration change', function () {
      expect(streamDurationMixin.updateParams).toHaveBeenCalledOnceWith({
        qs : {
          unit : 5,
          size : 'minutes'
        }
      });
    });

    it('should assign unit', function () {
      expect(streamDurationMixin.unit).toBe(5);
    });

    it('should assign size', function () {
      expect(streamDurationMixin.size).toBe('minutes');
    });
  });

  it('should do a full refresh if data is empty', function () {
    streamDurationMixin.size = 10;
    streamDurationMixin.unit = 'hours';

    streamDurationMixin.beforeStreaming('fakeMethod', params, cb);

    expect(cb).toHaveBeenCalledWith('fakeMethod', {
      qs: {
        unit: 'hours',
        size: 10
      }
    });
  });

  describe('before streaming full refresh', function () {
    beforeEach(function () {
      params.qs = {
        unit: 'minutes',
        size: 10,
        update: 'true',
        begin: '',
        end: '',
        fakeParam: 'fakeValue'
      };

      streamDurationMixin.beforeStreaming('fakeMethod', params, cb);
    });

    it('should remove unit, size, update, begin, and end from params', function () {
      expect(params).toEqual({
        qs: {
          fakeParam: 'fakeValue'
        }
      });
    });

    it('should call with method and params', function () {
      expect(cb).toHaveBeenCalledOnceWith('fakeMethod', {
        qs: {
          fakeParam: 'fakeValue'
        }
      });
    });
  });

  describe('before streaming update', function () {
    beforeEach(function () {
      data = [
        {
          values: [
            {x: new Date('12/09/2013')},
            {x: new Date('12/10/2013')},
            {x: new Date('12/11/2013')}
          ]
        }
      ];

      streamDurationMixin.beforeStreaming('fakeMethod', params, cb);
    });

    it('should set up params for an update', function () {
      expect(params).toEqual({
        qs : {
          update: true,
          begin: data[0].values[0].x.toISOString(),
          end: data[0].values[2].x.toISOString()
        }
      });
    });
  });
});