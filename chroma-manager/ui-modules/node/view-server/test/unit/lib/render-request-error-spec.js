'use strict';

var proxyquire = require('proxyquire').noPreserveCache();
var λ = require('highland');

describe('render request error', function () {
  var renderRequestError, getUname, templates, stream, res;

  beforeEach(function () {
    res = {
      clientRes: {
        end: jasmine.createSpy('end')
      }
    };

    templates = {
      'backend_error.html': jasmine.createSpy('backend error').and.returnValue('backend error')
    };

    stream = λ();

    getUname = jasmine.createSpy('getUname').and.returnValue(stream);

    renderRequestError = proxyquire('../../../lib/render-request-error', {
      './get-uname': getUname,
      './templates': templates
    });
  });

  it('should render a backend error', function () {
    renderRequestError(res, 'uh-oh', new Error('boom!'));

    stream.write({ corosync: 'STOPPED' });

    expect(templates['backend_error.html']).toHaveBeenCalledOnceWith({
      description: 'uh-oh',
      debug_info: { corosync: 'STOPPED' }
    });
  });

  it('should send the rendered body', function () {
    renderRequestError(res, 'uh-oh', new Error('boom!'));

    stream.write({ corosync: 'STOPPED' });

    expect(res.clientRes.end).toHaveBeenCalledOnceWith('backend error');
  });

  it('should handle a function for description', function () {
    renderRequestError(res, function (err) {
      return 'error was ' + err.message;
    }, new Error('boom!'));

    stream.write({ corosync: 'STOPPED' });

    expect(templates['backend_error.html']).toHaveBeenCalledOnceWith({
      description: 'error was boom!',
      debug_info: { corosync: 'STOPPED' }
    });
  });
});
