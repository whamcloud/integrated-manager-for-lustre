'use strict';

var serverFactory = require('../../server'),
  sinon = require('sinon');

require('jasmine-sinon');


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
      listen: sinon.spy()
    };

    https = {
      createServer: sinon.mock().returns(server)
    };

    serverFactory(conf, https);
  });

  it('should create the server with the provided files', function () {
    expect(https.createServer).toHaveBeenCalledWithExactly({
      cert: conf.certFile,
      key: conf.keyFile,
      ca: conf.caFile
    });
  });

  it('should listen on the primus port', function () {
    expect(server.listen).toHaveBeenCalledWithExactly(conf.primusPort);
  });
});