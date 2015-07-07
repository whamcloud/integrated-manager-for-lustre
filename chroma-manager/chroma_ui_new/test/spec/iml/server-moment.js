describe('Server Moment', function () {
  'use strict';

  var constants = {SERVER_TIME_DIFF: 2000};

  beforeEach(module('serverMoment', function($provide) {
    var momentInstance = {
      add: jasmine.createSpy('add')
    };
    momentInstance.add.andReturn(momentInstance);

    $provide.value('moment', jasmine.createSpy('moment').andReturn(momentInstance));
  }, constants));

  var moment, getServerMoment;

  beforeEach(inject(function (_moment_, _getServerMoment_) {
    moment = _moment_;
    getServerMoment = _getServerMoment_;
  }));

  it('should be a function', function () {
    expect(getServerMoment).toEqual(jasmine.any(Function));
  });

  it('should create a new moment', function () {
    var serverMoment = getServerMoment();

    expect(moment).toHaveBeenCalledOnce();
    expect(serverMoment).toEqual(moment.plan());
  });

  it('should add the server time diff', function () {
    getServerMoment();

    expect(moment.plan().add).toHaveBeenCalledOnceWith(constants.SERVER_TIME_DIFF);
  });

  it('should forward arguments to moment', function () {
    var epochTime = new Date().valueOf();

    getServerMoment(epochTime);

    expect(moment).toHaveBeenCalledOnceWith(epochTime);
  });
});
