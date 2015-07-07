describe('stream duration mixin', function () {
  'use strict';

  beforeEach(module('charts', 'mockServerMoment'));

  var streamDurationMixin, getServerMoment, cb, params;

  beforeEach(inject(function (_streamDurationMixin_, _getServerMoment_) {
    streamDurationMixin = _streamDurationMixin_;
    getServerMoment = _getServerMoment_;

    params = { qs: {} };

    cb = jasmine.createSpy('callback');

    streamDurationMixin.restart = jasmine.createSpy('restart');
    streamDurationMixin.getter = jasmine.createSpy('getter');
  }));

  /**
   * Configures moment.toISOString
   * to return begin and end based on
   * call count.
   * @param {String} begin
   * @param {String} end
   * @returns {Function}
   */
  function setupBeginEnd (begin, end) {
    return function getBeginOrEnd () {
      /*jshint validthis: true */
      switch (this.toISOString.callCount) {
        case 1:
          return end;
        case 2:
          return begin;
      }
    };
  }

  describe('duration change', function () {
    beforeEach(function () {
      streamDurationMixin.setDuration(5, 'minutes');
    });

    it('should set the updated duration flag', function () {
      expect(streamDurationMixin.updatedDuration).toBe(true);
    });

    it('should restart on duration change', function () {
      expect(streamDurationMixin.restart).toHaveBeenCalledOnce();
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

    var begin = '2014-04-29T05:33:38.533Z';
    var end = '2014-04-29T15:33:38.533Z';

    getServerMoment.plan().toISOString.andCallFake(setupBeginEnd(begin, end));

    streamDurationMixin.getter.andReturn([]);
    streamDurationMixin.beforeStreaming('fakeMethod', params, cb);

    expect(cb).toHaveBeenCalledWith('fakeMethod', {
      qs: {
        begin: begin,
        end: end
      }
    });
  });

  describe('before streaming full refresh', function () {
    var begin, end;

    beforeEach(function () {
      params.qs = {
        update: 'true',
        begin: '',
        end: '',
        fakeParam: 'fakeValue'
      };

      end = '2014-04-29T05:33:38.533Z';
      begin = '2014-04-29T05:23:38.533Z';

      getServerMoment.plan().toISOString.andCallFake(setupBeginEnd(begin, end));

      streamDurationMixin.updatedDuration = true;
      streamDurationMixin.beforeStreaming('fakeMethod', params, cb);
      streamDurationMixin.getter.andReturn([]);
    });

    it('should remove unit, size, and update from params', function () {
      expect(params).toEqual({
        qs: {
          fakeParam: 'fakeValue',
          begin: begin,
          end: end
        }
      });
    });

    it('should call with method and params', function () {
      expect(cb).toHaveBeenCalledOnceWith('fakeMethod', {
        qs: {
          fakeParam: 'fakeValue',
          begin: begin,
          end: end
        }
      });
    });

    it('should reset the updated duration flag', function () {
      expect(streamDurationMixin.updatedDuration).toBeFalsy();
    });
  });

  describe('before streaming update', function () {
    var data;

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

      streamDurationMixin.getter.andReturn(data);
      streamDurationMixin.beforeStreaming('fakeMethod', params, cb);
    });

    it('should set up params for an update', function () {
      expect(params).toEqual({
        qs: {
          update: true,
          begin: data[0].values[0].x.toISOString(),
          end: data[0].values[2].x.toISOString()
        }
      });
    });
  });
});
