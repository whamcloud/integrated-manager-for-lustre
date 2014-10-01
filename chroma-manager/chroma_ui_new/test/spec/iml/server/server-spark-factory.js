describe('server spark', function () {
  'use strict';

  var socket, CACHE_INITIAL_DATA;

  beforeEach(module('server', function ($provide) {
    socket = jasmine.createSpy('socket').andReturn({
      send: jasmine.createSpy('send'),
      on: jasmine.createSpy('on')
    });

    CACHE_INITIAL_DATA = {
      host: {}
    };

    $provide.constant('CACHE_INITIAL_DATA', CACHE_INITIAL_DATA);

    $provide.value('socket', socket);
  }));

  var serverSpark, spark;

  beforeEach(inject(function (_serverSpark_) {
    serverSpark = _serverSpark_;
    spark = serverSpark();
  }));

  it('should get the spark', function () {
    expect(socket).toHaveBeenCalledOnceWith('request');
  });

  it('should return the spark', function () {
    expect(spark).toEqual(jasmine.any(Object));
  });

  it('should set the last response', function () {
    expect(spark.lastArgs).toEqual([{
      statusCode: 200,
      body: {
        objects: {}
      }
    }]);
  });

  it('should send the request', function () {
    expect(spark.send).toHaveBeenCalledOnceWith('req', {
      path: '/host',
      options: {
        jsonMask : 'objects(id,address,available_actions,boot_time,fqdn,immutable_state,install_method,label,locks\
,member_of_available_filesystem,nids,nodename,resource_uri,server_profile,state)',
        qs: {
          limit: 0
        }
      }
    });
  });

  it('should listen for data', function () {
    expect(spark.on).toHaveBeenCalledOnceWith('data', jasmine.any(Function));
  });
});
