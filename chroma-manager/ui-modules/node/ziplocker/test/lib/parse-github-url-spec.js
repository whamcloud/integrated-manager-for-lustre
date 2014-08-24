'use strict';

var parseGithubUrlModule = require('../../lib/parse-github-url').wiretree;
var Promise = require('promise');

describe('Parse github url', function () {
  var parseGithubUrl;

  beforeEach(function () {
    parseGithubUrl = parseGithubUrlModule(Promise);
  });

  var dataProvider = [
    {
      url: 'git+https://github.com/michaelficarra/CoffeeScriptRedux.git#9895cd1641fdf3a2424e662ab7583726bb0e35b3',
      parsed: {
        path: 'michaelficarra/CoffeeScriptRedux.git',
        commitIsh: '9895cd1641fdf3a2424e662ab7583726bb0e35b3'
      }
    },
    {
      url: 'git://github.com/michaelficarra/cscodegen.git#73fd7202ac086c26f18c9d56f025b18b3c6f5383',
      parsed: {
        path: 'michaelficarra/cscodegen.git',
        commitIsh: '73fd7202ac086c26f18c9d56f025b18b3c6f5383'
      }
    },
    {
      url: 'pipobscure/fsevents#7dcdf9fa3f8956610fd6f69f72c67bace2de7138',
      parsed: {
        path: 'pipobscure/fsevents',
        commitIsh: '7dcdf9fa3f8956610fd6f69f72c67bace2de7138'
      }
    },
    {
      url: 'https://foo/bars'
    }
  ];

  dataProvider.forEach(function testUrls (item) {
    var promise;

    beforeEach(function () {
      promise = parseGithubUrl(item.url);
    });

    if ('parsed' in item)
      pit('should parse ' + item.url, function () {
        return promise.then(function assertParsed (parsed) {
          expect(parsed).toEqual(item.parsed);
        });
      });
    else
      pit('should reject for ' + item.url, function () {
        return promise.catch(function assertErr (err) {
          expect(err).toEqual(jasmine.any(Error));
        });
      });
  });
});
