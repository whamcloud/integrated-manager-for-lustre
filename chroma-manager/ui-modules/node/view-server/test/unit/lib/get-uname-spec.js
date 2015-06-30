'use strict';

var proxyquire = require('proxyquire').noPreserveCache();

describe('get uname', function () {
  var getUname, childProcess;

  beforeEach(function () {
    childProcess = {
      exec: jasmine.createSpy('exec').and.callFake(function (command, cb) {
        var commands = {
          'uname -m': 'x86_64\n',
          'uname -n': 'iml.local\n',
          'uname -r': '14.1.0\n',
          'uname -s': 'Darwin\n',
          'uname -v': 'Darwin Kernel Version 14.1.0: Mon Dec 22 23:10:38 PST 2014; \
 root:xnu-2782.10.72~2/RELEASE_X86_64\n'
        };

        cb(null, commands[command]);
      })
    };

    getUname = proxyquire('../../../lib/get-uname', {
      child_process: childProcess
    });
  });

  it('should return system information', function (done) {
    getUname()
      .apply(function (x) {
        expect(x).toEqual({
          sysname: 'x86_64',
          nodename: 'iml.local',
          release: '14.1.0',
          version: 'Darwin',
          machine: 'Darwin Kernel Version 14.1.0: Mon Dec 22 23:10:38 PST 2014;  root:xnu-2782.10.72~2/RELEASE_X86_64'
        });

        done();
      });
  });
});
