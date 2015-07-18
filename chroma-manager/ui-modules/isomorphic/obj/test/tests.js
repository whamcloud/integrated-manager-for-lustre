'use strict';

var obj = require('../index');

describe('obj module', function () {

  describe('merge function', function () {

    var obj1, obj2, obj3, obj4, obj5;
    beforeEach(function () {
      obj1 = {
        name: 'will',
        age: 33,
        hobby: 'surfing',
        prop1: {
          prop2: {
            some: 'val',
            foo: 'bar',
            prop3: {
              key: 'val'
            }
          }
        }
      };

      obj2 = {
        address: '123 ocean ave',
        state: 'FL',
        zip: '33617'
      };

      obj3 = {
        age: 2,
        make: 'gmc',
        model: 'terrain',
        prop1: {
          prop2: {
            baz: 'tastic',
            prop3: {
              a: '1',
              z: {
                turbo: true
              }
            }
          }
        }
      };

      obj4 = {
        key: 'val',
        names: ['will', 'nerissa', 'mariela', 'kali'],
        transportation: ['bike', 'car', 'bus'],
        fn: function funky () {
          console.log('uh uh uh, this isn\'t serializable.');
          return 1;
        }
      };

      obj5 = {
        names: ['joe', 'wayne', 'will'],
        transportation: {
          healthy: {
            bike: ['mountain', 'trick']
          },
          unhealthy: {
            car: ['2door', '4door'],
            bus: ['city', 'school']
          }
        }
      };
    });

    it('should throw an error when the rhs has a cycle', function () {
      obj3.prop1.prop2.prop3 = obj3.prop1;
      expect(function () { obj.merge(obj1, obj3); }).toThrow(new Error('Cycle detected, cannot merge.'));
    });

    it('should merge two objects together with a mutually exclusive domain of keys', function () {
      obj.merge(obj1, obj2);
      expect(obj1).toEqual(
        {
          name: 'will',
          age: 33,
          hobby: 'surfing',
          prop1: {
            prop2: {
              some: 'val',
              foo: 'bar',
              prop3: {
                key: 'val'
              }
            }
          },
          address: '123 ocean ave',
          state: 'FL',
          zip: '33617'
        }
      );
    });

    it('should merge objects together with overlapping keys', function () {
      obj.merge(obj1, obj2, obj3, obj4);
      expect(obj1).toEqual({
        name: 'will',
        age: 2,
        hobby: 'surfing',
        address: '123 ocean ave',
        state: 'FL',
        zip: '33617',
        prop1: {
          prop2: {
            some: 'val',
            foo: 'bar',
            baz: 'tastic',
            prop3: {
              key: 'val',
              a: '1',
              z: {
                turbo: true
              }
            }
          }
        },
        fn: jasmine.any(Function),
        make: 'gmc',
        model: 'terrain',
        key: 'val',
        names: ['will', 'nerissa', 'mariela', 'kali'],
        transportation: ['bike', 'car', 'bus']
      });
    });

    it('should verify that objects passed in after the first argument are not mutated', function () {
      obj.merge(obj1, obj3);
      expect(obj3).toEqual({
        age: 2,
        make: 'gmc',
        model: 'terrain',
        prop1: {
          prop2: {
            baz: 'tastic',
            prop3: {
              a: '1',
              z: {
                turbo: true
              }
            }
          }
        }
      });
    });

    it('should be variadic', function () {
      var result = obj.merge({}, {}, {}, {}, {}, {}, {}, {a: 1}, {b: 2}, obj1, {name: 'robert'});
      expect(result).toEqual({
        a: 1,
        b: 2,
        name: 'robert',
        age: 33,
        hobby: 'surfing',
        prop1: {
          prop2: {
            some: 'val',
            foo: 'bar',
            prop3: {
              key: 'val'
            }
          }
        }
      });
    });

    it('should function as a "defaults" operation', function () {
      var defaults = {
        a: 1,
        b: 2
      };

      var newObj = {
        a: 7,
        key: 'val'
      };

      var result = obj.merge({}, defaults, newObj);
      expect(result).toEqual({
        a: 7,
        b: 2,
        key: 'val'
      });
    });

    it('should return the same object if it is only passed one object', function () {
      var result = obj.merge(obj1);
      expect(result).toEqual(obj1);
    });

    it('should return undefined if it doesn\'t receive any args', function () {
      expect(obj.merge()).toEqual(undefined);
    });

    it('should overwrite arrays', function () {
      obj.merge(obj4, obj5);
      expect(obj4).toEqual({
        key: 'val',
        names: ['joe', 'wayne', 'will'],
        transportation: {
          healthy: {
            bike: ['mountain', 'trick']
          },
          unhealthy: {
            car: ['2door', '4door'],
            bus: ['city', 'school']
          }
        },
        fn: jasmine.any(Function)
      });
    });

    it('should be a reference to the original object and not a copy', function () {
      var result = obj.merge(obj1, obj2);
      expect(result).toBe(obj1);
    });

    ['7', 7, [1, 2, 3], function () {}, true].forEach(function (item) {
      it('should overwrite the object if you pass in a non object', function () {
        expect(obj.merge(obj1, item)).toBe(item);
      });
    });
  });

  describe('clone function', function () {

    var obj1, items;
    beforeEach(function () {
      obj1 = {
        name: 'will',
        residence: {
          address: '123 ocean dr.',
          state: 'FL',
        },
        prop1: {
          prop2: {
            prop3: {
              key: 'val'
            }
          }
        },
        phone: '1234567890'
      };

      items = ['sword', 'shield', 'potion'];
    });

    it('should clone an object', function () {
      expect(obj.clone(obj1)).toEqual({
        name: 'will',
        residence: {
          address: '123 ocean dr.',
          state: 'FL'
        },
        prop1: {
          prop2: {
            prop3: {
              key: 'val'
            }
          }
        },
        phone: '1234567890'
      });
    });

    it('should clone an array', function () {
      expect(obj.clone(items)).toEqual(['sword', 'shield', 'potion']);
    });

    it('should be a copy of the object and not a reference to it', function () {
      expect(obj.clone(obj1)).not.toBe(obj1);
    });

    it('should be a copy of the array and not a reference to it', function () {
      expect(obj.clone(items)).not.toBe(items);
    });

    it('should throw an error if a cycle is detected', function () {
      obj1.prop1.prop2.prop3 = obj1.prop1;
      expect(function () { obj.clone(obj1); }).toThrowError(TypeError, 'Converting circular structure to JSON');
    });

    it('should not serialize non-serializable items', function () {
      obj1.prop1 = function prop1Fn () {};

      expect(obj.clone(obj1)).toEqual({
        name: 'will',
        residence: {
          address: '123 ocean dr.',
          state: 'FL'
        },
        phone: '1234567890'
      });
    });
  });
});
