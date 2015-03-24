'use strict';

var getSessionFactory = require('../../../../view-server/middleware/get-session').wiretree;
var λ = require('highland');

describe('get session', function () {
  var getSession, requestStream, renderRequestError, renderRequestErrorInner, req, res, next,
    push;

  beforeEach(function () {
    req = {
      clientReq: {
        headers: {
          cookie: 'foo'
        }
      }
    };

    res = {
      clientRes: {
        setHeader: jasmine.createSpy('setHeader')
      }
    };

    next = jasmine.createSpy('next');

    requestStream = jasmine.createSpy('requestStream').and.returnValue(λ(function (_push_) {
      push = function (err, val) {
        _push_(err, val);
        _push_(null, nil);
      };
    }));

    renderRequestErrorInner = jasmine.createSpy('renderRequestErrorInner');

    renderRequestError = jasmine.createSpy('renderRequestError')
      .and.returnValue(renderRequestErrorInner);

    getSession = getSessionFactory(requestStream, renderRequestError);

    getSession(req, res, next);
  });

  it('should get a session', function () {
    expect(requestStream).toHaveBeenCalledOnceWith('/session', {
      headers: {
        cookie: 'foo'
      }
    });
  });

  it('should pass session data to the next function', function () {
    push(null, {
      headers: {
        'set-cookie': [
          'csrftoken=0GkwjZHBUq1DoLeg7M3cEfod8d0EjAAn; expires=Mon, 08-Feb-2016 17:12:32 GMT; Max-Age=31449600; Path=/',
          'sessionid=7dbd643025680726843284b5ba7402b1; expires=Mon, 23-Feb-2015 17:12:32 GMT; Max-Age=1209600; Path=/'
        ]
      },
      body: {session: 'stuff'}
    });

    expect(next).toHaveBeenCalledOnceWith(req, res, {
      session: { session: 'stuff' },
      cacheCookie: 'csrftoken=0GkwjZHBUq1DoLeg7M3cEfod8d0EjAAn; sessionid=7dbd643025680726843284b5ba7402b1;'
    });
  });

  it('should stop on error', function () {
    push(new Error('boom!'));

    expect(renderRequestErrorInner).toHaveBeenCalledOnceWith(new Error('boom!'), jasmine.any(Function));
  });
});
