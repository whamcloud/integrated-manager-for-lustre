'use strict';

var addCredentials = require('../../../../socket-router/middleware/add-credentials');

describe('add credentials', function () {
  var next, req, resp;

  beforeEach(function () {
    next = jasmine.createSpy('next');

    req = { data: {} };

    resp = {
      socket: {
        request: {
          headers: {
            'user-agent': 'bar'
          }
        }
      }
    };
  });

  it('should call next with empty headers', function () {
    addCredentials(req, resp, next);

    expect(next).toHaveBeenCalledOnceWith(
      {
        data: {
          headers: {
            'User-Agent': 'bar'
          }
        }
      },
      {
        socket: {
          request: {
            headers: {
              'user-agent': 'bar'
            }
          }
        }
      }
    );
  });

  it('should set cookie, CSRF token, and user-agent headers', function () {
    resp.socket.request.headers = {
      cookie: 'csrftoken=z2WVzbtXqNvydVFACW8HlCyVpebt82M1; sessionid=a948605f1cb2dc8b1e929b8371d41a45',
      'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) \
Chrome/39.0.2171.95 Safari/537.36'
    };

    addCredentials(req, resp, next);

    expect(next).toHaveBeenCalledOnceWith(
      {
        data: {
          headers: {
            Cookie: 'csrftoken=z2WVzbtXqNvydVFACW8HlCyVpebt82M1; sessionid=a948605f1cb2dc8b1e929b8371d41a45',
            'X-CSRFToken': 'z2WVzbtXqNvydVFACW8HlCyVpebt82M1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) \
Chrome/39.0.2171.95 Safari/537.36'
          }
        }
      },
      {
        socket: {
          request: {
            headers: {
              cookie: 'csrftoken=z2WVzbtXqNvydVFACW8HlCyVpebt82M1; sessionid=a948605f1cb2dc8b1e929b8371d41a45',
              'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) \
Chrome/39.0.2171.95 Safari/537.36'
            }
          }
        }
      }
    );
  });

  it('should merge with existing headers', function () {
    req.data.headers = {
      'X-Foo-Header': 'foo'
    };

    addCredentials(req, resp, next);

    expect(next).toHaveBeenCalledOnceWith(
      {
        data: {
          headers: {
            'X-Foo-Header': 'foo',
            'User-Agent': 'bar'
          }
        }
      },
      {
        socket: {
          request: {
            headers: {
              'user-agent': 'bar'
            }
          }
        }
      }
    );
  });

  it('should not override existing headers', function () {
    req.data.headers = {
      'User-Agent': 'use this header'
    };

    addCredentials(req, resp, next);

    expect(next).toHaveBeenCalledOnceWith(
      {
        data: {
          headers: {
            'User-Agent': 'use this header'
          }
        }
      },
      {
        socket: {
          request: {
            headers: {
              'user-agent': 'bar'
            }
          }
        }
      }
    );
  });
});
