'use strict';

var groupAllowed = require('../../../lib/group-allowed');
var GROUPS = require('../../../lib/groups');

describe('group allowed', function () {
  it('should disallow no session', function () {
    expect(groupAllowed(GROUPS.FS_USERS, null)).toBeFalsy();
  });

  it('should disallow fs users and admins for superuser level permissions', function () {
    expect(groupAllowed(GROUPS.SUPERUSERS, {
      user: {
        groups: [
          { name: GROUPS.FS_ADMINS },
          { name: GROUPS.FS_USERS }
        ]
      }
    })).toBe(false);
  });

  it('should allow superusers', function () {
    expect(groupAllowed(GROUPS.SUPERUSERS, {
      user: {
        groups: [
          { name: GROUPS.FS_ADMINS },
          { name: GROUPS.FS_USERS },
          { name: GROUPS.SUPERUSERS }
        ]
      }
    })).toBe(true);
  });

  it('should allow fs users', function () {
    expect(groupAllowed(GROUPS.FS_USERS, {
      user: {
        groups: [
          { name: GROUPS.FS_USERS }
        ]
      }
    })).toBe(true);
  });

  it('should allow fs admins', function () {
    expect(groupAllowed(GROUPS.FS_ADMINS, {
      user: {
        groups: [
          { name: GROUPS.FS_ADMINS }
        ]
      }
    })).toBe(true);
  });
});
