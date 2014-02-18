'use strict';

var serverFactory = require('../../server');

describe('server', function () {
  var https, conf, server;

  beforeEach(function () {
    conf = {
      certFile: 'foo',
      keyFile: 'bar',
      caFile: 'baz',
      primusPort: 8888
    };

    server = {
      listen: jasmine.createSpy('server.listen')
    };

    https = {
      createServer: jasmine.createSpy('https.createServer').andReturn(server),
      globalAgent: {}
    };

    serverFactory(conf, https);
  });

  it('should set globalAgent.maxSockets to 25', function () {
    expect(https.globalAgent.maxSockets).toBe(25);
  });

  it('should create the server with the provided files', function () {
    expect(https.createServer).toHaveBeenCalledOnceWith({
      cert: conf.certFile,
      key: conf.keyFile,
      ca: conf.caFile
    });
  });

  it('should listen on the primus port', function () {
    expect(server.listen).toHaveBeenCalledOnceWith(conf.primusPort);
  });
});