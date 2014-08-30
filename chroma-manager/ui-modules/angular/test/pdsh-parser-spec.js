describe('pdsh parser', function () {
  'use strict';

  var parser;

  beforeEach(module('pdsh-parser-module'));

  beforeEach(inject(function (pdshParser) {
    parser = pdshParser;
  }));

  var tests = [
    {
      expression: 'hostname1.iml.com',
      expanded: {
        expansion: ['hostname1.iml.com']
      }
    },
    {
      expression: 'hostname1.iml.com, hostname2.iml.com',
      expanded: {
        expansion: ['hostname1.iml.com', 'hostname2.iml.com']
      }
    },
    {
      expression: 'hostname[6].iml.com',
      expanded: {
        expansion: ['hostname6.iml.com']
      }
    },
    {
      expression: 'hostname[6]',
      expanded: {
        expansion: ['hostname6']
      }
    },
    {
      expression: 'hostname[09-011]',
      expanded: {
        expansion: ['hostname09', 'hostname010', 'hostname011']
      }
    },
    {
      expression: 'hostname[009-0011]',
      expanded: {
        expansion: ['hostname009', 'hostname0010', 'hostname0011']
      }
    },
    {
      expression: 'hostname[2,6,7].iml.com,hostname[10,11-12,2-3,5].iml.com, hostname[15-17].iml.com',
      expanded: {
        expansion: ['hostname2.iml.com', 'hostname6.iml.com', 'hostname7.iml.com', 'hostname10.iml.com',
          'hostname11.iml.com', 'hostname12.iml.com', 'hostname3.iml.com', 'hostname5.iml.com', 'hostname15.iml.com',
          'hostname16.iml.com', 'hostname17.iml.com']
      }
    },
    {
      expression: 'hostname[6,7]-[9-11].iml.com',
      expanded: {
        expansion: ['hostname6-9.iml.com', 'hostname6-10.iml.com', 'hostname6-11.iml.com',
          'hostname7-9.iml.com', 'hostname7-10.iml.com', 'hostname7-11.iml.com']
      }
    },
    {
      expression: 'hostname[7,9-11].iml.com',
      expanded: {
        expansion: ['hostname7.iml.com', 'hostname9.iml.com', 'hostname10.iml.com', 'hostname11.iml.com']
      }
    },
    {
      expression: 'hostname[0-3]-eth0.iml.com',
      expanded: {
        expansion: ['hostname0-eth0.iml.com', 'hostname1-eth0.iml.com',
          'hostname2-eth0.iml.com', 'hostname3-eth0.iml.com']
      }
    },
    {
      expression: 'hostname[1,2]-[3-4]-[5,6].iml.com',
      expanded: {
        expansion: ['hostname1-3-5.iml.com', 'hostname1-3-6.iml.com', 'hostname1-4-5.iml.com', 'hostname1-4-6.iml.com',
          'hostname2-3-5.iml.com', 'hostname2-3-6.iml.com', 'hostname2-4-5.iml.com', 'hostname2-4-6.iml.com']
      }
    },
    {
      expression: 'test[000-002].localdomain',
      expanded: {
        expansion: ['test000.localdomain', 'test001.localdomain', 'test002.localdomain']
      }
    },
    {
      expression: 'test[00☃-002].localdomain',
      expanded: {
        errors: ['Range is not in the proper format.']
      }
    },
    {
      expression: '',
      expanded: {
        errors: ['Expression cannot be empty.']
      }
    },
    {
      expression: 'hostname[1,,2].iml.com',
      expanded: {
        errors: ['Range is not in the proper format.']
      }
    },
    {
      expression: 'hostname[1--2].iml.com',
      expanded: {
        errors: ['Range is not in the proper format.']
      }
    },
    {
      expression: 'hostname[1-,2].iml.com',
      expanded: {
        errors: ['Range is not in the proper format.']
      }
    },
    {
      expression: 'hostname[1,-2].iml.com',
      expanded: {
        errors: ['Range is not in the proper format.']
      }
    },
    {
      expression: 'hostname[1',
      expanded: {
        errors: ['Expression is invalid']
      }
    },
    {
      expression: 'hostname[1],',
      expanded: {
        errors: ['Expression is invalid']
      }
    },
    {
      expression: 'hostname[06-10]',
      expanded: {
        errors: ['Beginning and ending prefixes don\'t match']
      }
    },
    {
      expression: 'hostname[01-009]',
      expanded: {
        errors: ['Beginning and ending prefixes don\'t match']
      }
    },
    {
      // We ran into an issue where any time we have a closing bracket before an open bracket.
      expression: 'hostname]00[asdf',
      expanded: {
        errors: ['Expression is invalid']
      }
    }
  ];

  tests.forEach(function runTest (test) {
    it('should return correct expression ' + test.expression, function expectFirst () {
      var result = parser(test.expression);

      expect(result).toEqual(test.expanded);
    });
  });
});
