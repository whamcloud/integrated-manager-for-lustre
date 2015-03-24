'use strict';

var lodash = require('lodash-mixins');
var templatesFactory = require('../../../lib/templates').wiretree;

describe('templates', function () {
  var templates, conf, getDirTreeSync;

  beforeEach(function () {
    getDirTreeSync = jasmine.createSpy('getDirTreeSync')
      .and.returnValue({
        'e.html': '<$= a $> <$= t("f.html") $> <$= conf.templateRoot $> <$- html $>',
        'f.html': 'bar'
      });

    conf = {
      templateRoot: '/a/b/c'
    };

    templates = templatesFactory(getDirTreeSync, lodash, conf);
  });

  it('should populate a template as expected', function () {
    expect(templates['e.html']({ a: 'a', html: '<script>console.log("foo");</script>' }))
      .toEqual('a bar /a/b/c &lt;script&gt;console.log(&quot;foo&quot;);&lt;/script&gt;');
  });
});
