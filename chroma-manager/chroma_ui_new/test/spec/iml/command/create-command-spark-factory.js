describe('create the command spark', function () {
  'use strict';

  var requestSocket, commandTransform, createCommandSpark, commandList, spark, result;

  beforeEach(module('command', function ($provide) {

    spark = {
      sendGet: jasmine.createSpy('sendPost'),
      setLastData: jasmine.createSpy('setLastData'),
      addPipe: jasmine.createSpy('addPipe')
    };

    requestSocket = jasmine.createSpy('requestSocket').andReturn(spark);
    $provide.value('requestSocket', requestSocket);

    commandTransform = jasmine.createSpy('commandTransform');
    $provide.value('commandTransform', commandTransform);
  }));

  beforeEach(inject(function (_createCommandSpark_) {
    createCommandSpark = _createCommandSpark_;
    commandList = [
      {
        id: 123,
        other: 'other',
        arg: 'arg'
      },
      {
        id: 456,
        more: 'more',
        props: 'props'
      }
    ];

    result = createCommandSpark(commandList);
  }));

  it('should invoke requestSocket', function () {
    expect(requestSocket).toHaveBeenCalledOnce();
  });

  it('should call spark.setLastData', function () {
    expect(spark.setLastData).toHaveBeenCalledOnceWith({
      body: {
        objects: commandList
      }
    });
  });

  it('should call spark.addPipe', function () {
    expect(spark.addPipe).toHaveBeenCalledOnceWith(commandTransform);
  });

  it('should call spark.sendGet', function () {
    var options = {
      qs: {
        id__in: [123, 456]
      }
    };
    expect(spark.sendGet).toHaveBeenCalledOnceWith('/command', options);
  });

  it('should return the spark', function () {
    expect(result).toBe(spark);
  });
});
