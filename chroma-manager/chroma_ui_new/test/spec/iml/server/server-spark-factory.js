describe('server spark', function () {
  'use strict';

  var requestSocket, CACHE_INITIAL_DATA;

  beforeEach(module('server', function ($provide) {
    requestSocket = jasmine.createSpy('requestSocket').andReturn({
      sendGet: jasmine.createSpy('sendGet'),
      on: jasmine.createSpy('on'),
      setLastData: jasmine.createSpy('setLastData')
    });

    CACHE_INITIAL_DATA = {
      host: {}
    };

    $provide.constant('CACHE_INITIAL_DATA', CACHE_INITIAL_DATA);

    $provide.value('requestSocket', requestSocket);
  }));

  var serverSpark, spark;

  beforeEach(inject(function (_serverSpark_) {
    serverSpark = _serverSpark_;
    spark = serverSpark();
  }));

  it('should get the spark', function () {
    expect(requestSocket).toHaveBeenCalledOnce();
  });

  it('should return the spark', function () {
    expect(spark).toEqual(jasmine.any(Object));
  });

  it('should set the last response', function () {
    expect(spark.setLastData).toHaveBeenCalledOnceWith({
      statusCode: 200,
      body: {
        objects: {}
      }
    });
  });

  it('should send the request', function () {
    expect(spark.sendGet).toHaveBeenCalledOnceWith('/host', {
      jsonMask: 'objects(id,address,available_actions,boot_time,fqdn,immutable_state,install_method,label,locks\
,member_of_active_filesystem,nids,nodename,resource_uri,server_profile,state)',
      qs: {
        limit: 0
      }
    });
  });

  it('should listen for data', function () {
    expect(spark.on).toHaveBeenCalledOnceWith('data', jasmine.any(Function));
  });
});
