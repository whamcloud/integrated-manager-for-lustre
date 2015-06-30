'use strict';

var proxyquire = require('proxyquire').noPreserveCache();

describe('index handlers', function () {
  var indexHandlers, templates, conf, req, res, data, next;

  beforeEach(function () {
    req = {};

    res = {
      clientRes: {
        setHeader: jasmine.createSpy('setHeader'),
        end: jasmine.createSpy('end')
      },
      redirect: jasmine.createSpy('redirect')
    };

    data = {
      cache: {
        session: {
          user: {}
        }
      }
    };

    next = jasmine.createSpy('next');

    templates = {
      'new/index.html': jasmine.createSpy('index').and.returnValue('index'),
      'base.html': jasmine.createSpy('base').and.returnValue('base')
    };

    conf = { allowAnonymousRead: false };

    indexHandlers = proxyquire('../../../lib/index-handlers', {
      './templates': templates,
      '../conf': conf
    });
  });

  it('should redirect if we don\'t have a user and disallow anonymous read', function () {
    delete data.cache.session.user;

    indexHandlers.newHandler(req, res, data, next);

    expect(res.redirect).toHaveBeenCalledOnceWith('/ui/login/');
  });

  it('should set the response header', function () {
    indexHandlers.newHandler(req, res, data, next);

    expect(res.clientRes.setHeader).toHaveBeenCalledOnceWith('Content-Type', 'text/html; charset=utf-8');
  });

  it('should set the status code', function () {
    indexHandlers.newHandler(req, res, data, next);

    expect(res.clientRes.statusCode).toBe(200);
  });

  it('should render the template', function () {
    indexHandlers.newHandler(req, res, data, next);

    expect(templates['new/index.html']).toHaveBeenCalledOnceWith({
      title: '',
      cache: data.cache
    });
  });

  it('should render the old template', function () {
    indexHandlers.oldHandler(req, res, data, next);

    expect(templates['base.html']).toHaveBeenCalledOnceWith({
      title: '',
      cache: data.cache
    });
  });

  it('should end the response', function () {
    indexHandlers.newHandler(req, res, data, next);

    expect(res.clientRes.end).toHaveBeenCalledOnceWith('index');
  });

  it('should call next', function () {
    indexHandlers.newHandler(req, res, data, next);

    expect(next).toHaveBeenCalledOnceWith(req, res);
  });
});
