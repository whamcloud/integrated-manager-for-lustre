angular.module('fixtures', []).service('fixtures', function () {
  'use strict';

  var fixtures = {};

  this.registerFixture = function registerFixture (name, status, data, headers) {
    if (_.isPlainObject(status)) {
      data = status;
      status = 200;
    }

    var fixture = {
      status: status,
      data: data,
      toArray: function () {
        var out = [this.status, this.data];

        if (this.headers) {
          out.push(this.headers);
        }

        return out;
      }
    };

    if (headers) {
      fixture.headers = headers;
    }

    var group = fixtures[name] = fixtures[name] || [];

    group.push(fixture);

    return this;
  };

  this.asName = function (name) {
    return {
      getFixtures: this.getFixtures.bind(this, name),
      getFixture: this.getFixture.bind(this, name)
    };
  };

  this.getFixtures = function (name, filter) {
    var group = fixtures[name] || [];

    return group.filter(filter);
  };

  this.getFixture = function (name, filter) {
    var group = fixtures[name] || [];

    var fixture = group.filter(filter)[0];

    if (!fixture)
      throw new Error('No matching fixtures found under %s!'.sprintf(name));

    return _.cloneDeep(fixture);
  };
});
