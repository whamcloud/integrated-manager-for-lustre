'use strict';

var λ = require('highland');
var checkGroupFactory = require('../../../lib/check-group').wiretree;
var GROUPS = require('../../../lib/groups').wiretree();
var groupAllowed = require('../../../lib/group-allowed').wiretree(λ, GROUPS);
var lodash = require('lodash-mixins');

describe('check group', function () {
  var checkGroup, req, res, data, next;

  beforeEach(function () {
    req = {};
    res = {
      redirect: jasmine.createSpy('redirect')
    };
    data = {
      cache: {
        session: {}
      }
    };
    next = jasmine.createSpy('next');

    checkGroup = checkGroupFactory(lodash, groupAllowed, GROUPS);
  });

  it('should return the expected interface', function () {
    expect(checkGroup).toEqual({
      superusers: jasmine.any(Function),
      fsAdmins: jasmine.any(Function),
      fsUsers: jasmine.any(Function)
    });
  });

  it('should allow superusers', function () {
    data.cache.session.user = {
      groups: [
        { name: GROUPS.SUPERUSERS }
      ]
    };

    checkGroup.superusers(req, res, data, next);

    expect(next).toHaveBeenCalledOnceWith(req, res, data);
  });

  it('should redirect fs admins', function () {
    data.cache.session.user = {
      groups: [
        { name: GROUPS.FS_ADMINS }
      ]
    };

    checkGroup.superusers(req, res, data, next);

    expect(res.redirect).toHaveBeenCalledOnceWith('/ui/');
  });

  it('should redirect fs users', function () {
    data.cache.session.user = {
      groups: [
        { name: GROUPS.FS_USERS }
      ]
    };

    checkGroup.superusers(req, res, data, next);

    expect(res.redirect).toHaveBeenCalledOnceWith('/ui/');
  });
});
