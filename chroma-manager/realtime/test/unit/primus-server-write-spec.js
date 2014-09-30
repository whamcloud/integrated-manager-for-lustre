'use strict';

var primusServerWriteFactory = require('../../primus-server-write');
var _ = require('lodash-mixins');
var format = require('util').format;

describe('primus server write plugin', function () {
  var errorSerializer, proto;

  beforeEach(function () {
    errorSerializer = jasmine.createSpy('errorSerializer').andCallFake(_.identity);

    function MultiplexSpark () {}
    MultiplexSpark.prototype = proto = {
      write: jasmine.createSpy('write'),
      end: jasmine.createSpy('end')
    };

    primusServerWriteFactory(errorSerializer, MultiplexSpark).server();
  });

  ['response', 'error'].forEach(function testType (type) {
    var capType = capitalize(type);
    var error = new Error('foo');
    error.statusCode = 400;
    var errorData = {
      args: [400, new Error('foo')],
      expected: {
        statusCode: 400,
        error: error
      }
    };
    var responseData = {
      args: [200, { foo: 'bar' }],
      expected: {
        statusCode: 200,
        body: { foo: 'bar' }
      }
    };
    var data = (type === 'error' ? errorData : responseData);


    it(format('should add a get%sFormat to MultiplexSpark', capType), function () {
      expect(proto[format('get%sFormat', capType)]).toEqual(jasmine.any(Function));
    });

    it(format('should add a write%s to MultiplexSpark', capType), function () {
      expect(proto['write' + capType]).toEqual(jasmine.any(Function));
    });

    it(format('should add an end%s to MultiplexSpark', capType), function () {
      expect(proto['end' + capType]).toEqual(jasmine.any(Function));
    });

    it(format('should return the %s format', type), function () {
      expect(proto[format('get%sFormat', capType)].apply(proto, data.args)).toEqual(data.expected);
    });

    it(format('should end the %s on the spark', type), function () {
      proto['end' + capType].apply(proto, data.args);

      expect(proto.end).toHaveBeenCalledOnceWith(data.expected);
    });

    it(format('should write the %s on the spark', type), function () {
      proto['write' + capType].apply(proto, data.args);

      expect(proto.write).toHaveBeenCalledOnceWith(data.expected);
    });
  });
});

/**
 * Capitalize a string
 * @param {String} str
 * @returns {string}
 */
function capitalize (str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}
