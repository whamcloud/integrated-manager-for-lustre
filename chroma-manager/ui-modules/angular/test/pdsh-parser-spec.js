describe('pdsh parser', function () {
  'use strict';

  var parser;

  beforeEach(module('pdsh-parser-module'));

  beforeEach(inject(function (pdshParser) {
    parser = pdshParser;
  }));

  var nameWithId = _.curry(function getNameWithId(name, id) {
    return name.sprintf(id);
  });

  var idInObject = _.curry(function addIdToObject(name, obj, id) {
    obj[nameWithId(name, id)] = 1;
    return obj;
  });


  var tests = [
    // single item without ranges
    {
      expression: 'hostname1.iml.com',
      expanded: {
        expansion: ['hostname1.iml.com'],
        sections: ['hostname1.iml.com'],
        expansionHash : { 'hostname1.iml.com' : 1 }
      }
    },
    // two items without ranges
    {
      expression: 'hostname1.iml.com, hostname2.iml.com',
      expanded: {
        expansion: ['hostname1.iml.com', 'hostname2.iml.com'],
        sections: ['hostname1.iml.com', 'hostname2.iml.com'],
        expansionHash: {
          'hostname1.iml.com': 1,
          'hostname2.iml.com': 1
        }
      }
    },
    // single item with single range
    {
      expression: 'hostname[6].iml.com',
      expanded: {
        expansion: ['hostname6.iml.com'],
        sections: ['hostname6.iml.com'],
        expansionHash: {
          'hostname6.iml.com': 1
        }
      }
    },
    // single item with single range and nothing after the range
    {
      expression: 'hostname[6]',
      expanded: {
        expansion: ['hostname6'],
        sections: ['hostname6'],
        expansionHash: {
          'hostname6': 1
        }
      }
    },
    // single item with single digit prefixed range
    {
      expression: 'hostname[09-11]',
      expanded: {
        expansion: ['hostname09', 'hostname10', 'hostname11'],
        sections: ['hostname09..11'],
        expansionHash : {
          hostname09 : 1,
          hostname10 : 1,
          hostname11 : 1
        }
      }
    },
    // single item with double digit prefixed range
    {
      expression: 'hostname[009-011]',
      expanded: {
        expansion: ['hostname009', 'hostname010', 'hostname011'],
        sections: ['hostname009..011'],
        expansionHash : {
          hostname009 : 1,
          hostname010 : 1,
          hostname011 : 1
        }
      }
    },
    // long range with prefix
    {
      expression: 'hostname[001-999]',
      expanded: {
        expansion: _.range(1, 10).map(nameWithId('hostname00%s'))
          .concat(_.range(10, 100).map(nameWithId('hostname0%s')))
            .concat(_.range(100, 1000).map(nameWithId('hostname%s'))),
        sections: ['hostname001..999'],
        expansionHash: _.chain(_.range(1, 10).reduce(idInObject('hostname00%s'), {}))
          .merge(_.range(10, 100).reduce(idInObject('hostname0%s'), {}))
          .merge(_.range(100, 1000).reduce(idInObject('hostname%s'), {})).value()
      }
    },
    // single item with two ranges
    {
      expression: 'hostname[6,7]-[9-11].iml.com',
      expanded: {
        expansion: ['hostname6-9.iml.com', 'hostname6-10.iml.com', 'hostname6-11.iml.com',
          'hostname7-9.iml.com', 'hostname7-10.iml.com', 'hostname7-11.iml.com'],
        sections:  ['hostname6..7-9..11.iml.com'],
        expansionHash : {
          'hostname6-9.iml.com' : 1,
          'hostname6-10.iml.com' : 1,
          'hostname6-11.iml.com' : 1,
          'hostname7-9.iml.com' : 1,
          'hostname7-10.iml.com' : 1,
          'hostname7-11.iml.com' : 1
        }
      }
    },
    // single item with range containing mixture of comma and dash
    {
      expression: 'hostname[7,9-11].iml.com',
      expanded: {
        expansion: ['hostname7.iml.com', 'hostname9.iml.com', 'hostname10.iml.com', 'hostname11.iml.com'],
        sections: ['hostname7.iml.com', 'hostname9..11.iml.com'],
        expansionHash : {
          'hostname7.iml.com' : 1,
          'hostname9.iml.com' : 1,
          'hostname10.iml.com' : 1,
          'hostname11.iml.com' : 1
        }
      }
    },
    // Single range per hostname in which the difference between ranges is clearly 1 so they can be combined. A
    // duplicate was also added here to verify that it is removed.
    {
      expression: 'hostname[2,6,7].iml.com,hostname[10,11-12,2-4,5].iml.com, hostname[15-17].iml.com',
      expanded: {
        expansion: [ 'hostname2.iml.com', 'hostname3.iml.com', 'hostname4.iml.com', 'hostname5.iml.com',
          'hostname6.iml.com', 'hostname7.iml.com', 'hostname10.iml.com', 'hostname11.iml.com', 'hostname12.iml.com',
          'hostname15.iml.com', 'hostname16.iml.com', 'hostname17.iml.com' ],
        sections: [ 'hostname2..7.iml.com', 'hostname10..12.iml.com', 'hostname15..17.iml.com' ],
        expansionHash : {
          'hostname2.iml.com' : 1,
          'hostname6.iml.com' : 1,
          'hostname7.iml.com' : 1,
          'hostname10.iml.com' : 1,
          'hostname11.iml.com' : 1,
          'hostname12.iml.com' : 1,
          'hostname3.iml.com' : 1,
          'hostname4.iml.com' : 1,
          'hostname5.iml.com' : 1,
          'hostname15.iml.com' : 1,
          'hostname16.iml.com' : 1,
          'hostname17.iml.com' : 1
        }
      }
    },
    // Multiple ranges per hostname in which the difference is 1 (first item is the same) using the same range format
    {
      expression: 'hostname[1,2-3].iml[2,3].com,hostname[3,4,5].iml[2,3].com,hostname[5-6,7].iml[2,3].com',
      expanded: {
        expansion: [
          'hostname1.iml2.com', 'hostname1.iml3.com','hostname2.iml2.com', 'hostname2.iml3.com',
          'hostname3.iml2.com', 'hostname3.iml3.com',
          'hostname4.iml2.com', 'hostname4.iml3.com', 'hostname5.iml2.com',
          'hostname5.iml3.com', 'hostname6.iml2.com', 'hostname6.iml3.com',
          'hostname7.iml2.com', 'hostname7.iml3.com'],
        sections: ['hostname1..7.iml2..3.com'],
        expansionHash : {
          'hostname1.iml2.com' : 1,
          'hostname1.iml3.com' : 1,
          'hostname2.iml2.com' : 1,
          'hostname2.iml3.com' : 1,
          'hostname3.iml2.com' : 1,
          'hostname3.iml3.com' : 1,
          'hostname4.iml2.com' : 1,
          'hostname4.iml3.com' : 1,
          'hostname5.iml2.com' : 1,
          'hostname5.iml3.com' : 1,
          'hostname6.iml2.com' : 1,
          'hostname6.iml3.com' : 1,
          'hostname7.iml2.com' : 1,
          'hostname7.iml3.com' : 1
        }
      }
    },
    // Multiple ranges per hostname in which the difference is 1 (second item is the same) using two formats that
    // when expanded are equal
    {
      expression: 'hostname[1,2-3].iml[2,3].com,hostname[1,2,3].iml[2,4].com',
      expanded: {
        expansion: [
          'hostname1.iml2.com', 'hostname1.iml3.com', 'hostname1.iml4.com',
          'hostname2.iml2.com', 'hostname2.iml3.com', 'hostname2.iml4.com',
          'hostname3.iml2.com', 'hostname3.iml3.com', 'hostname3.iml4.com'],
        sections: ['hostname1..3.iml2..4.com'],
        expansionHash : {
          'hostname1.iml2.com' : 1,
          'hostname1.iml3.com' : 1,
          'hostname1.iml4.com' : 1,
          'hostname2.iml2.com' : 1,
          'hostname2.iml3.com' : 1,
          'hostname2.iml4.com' : 1,
          'hostname3.iml2.com' : 1,
          'hostname3.iml3.com' : 1,
          'hostname3.iml4.com' : 1
        }
      }
    },
    // Multiple ranges per hostname in which the difference is > 1
    {
      expression: 'hostname[1,2-3].iml[2,3].com,hostname[4,5].iml[3,4].com',
      expanded: {
        expansion: [
          'hostname1.iml2.com', 'hostname1.iml3.com','hostname2.iml2.com',
          'hostname2.iml3.com','hostname3.iml2.com', 'hostname3.iml3.com',
          'hostname4.iml3.com', 'hostname4.iml4.com', 'hostname5.iml3.com',
          'hostname5.iml4.com'],
        sections: ['hostname1..3.iml2..3.com', 'hostname4..5.iml3..4.com'],
        expansionHash : {
          'hostname1.iml2.com' : 1,
          'hostname1.iml3.com' : 1,
          'hostname2.iml2.com' : 1,
          'hostname2.iml3.com' : 1,
          'hostname3.iml2.com' : 1,
          'hostname3.iml3.com' : 1,
          'hostname4.iml3.com' : 1,
          'hostname4.iml4.com' : 1,
          'hostname5.iml3.com' : 1,
          'hostname5.iml4.com' : 1
        }
      }
    },
    // no prefix to prefix should throw an error
    {
      expression: 'hostname[9-0011]',
      expanded: {
        errors: ['Number of digits must be consistent across padded entries']
      }
    },
    // Duplicate occurring when the difference between ranges is > 1. In this case, the duplicate
    // can't be detected because the expressions cannot be combined.
    {
      expression: 'hostname[1,2-3].iml[2,3].com,hostname[3,4,5].iml[3,4].com',
      expanded: {
        errors: [ 'Expression hostname[3,4,5].iml[3,4].com matches previous expansion of hostname3.iml3.com generated' +
          ' by hostname[1,2-3].iml[2,3].com' ]
      }
    },
    // Duplicate without using a range
    {
      expression: 'hostname4.iml.com,hostname4.iml.com',
      expanded: {
        errors : [ 'Expression  matches previous expansion of hostname4.iml.com generated by hostname4.iml.com' ]
      }
    },
    // Single item with single range and additional characters after range
    {
      expression: 'hostname[0-3]-eth0.iml.com',
      expanded: {
        expansion: ['hostname0-eth0.iml.com', 'hostname1-eth0.iml.com',
          'hostname2-eth0.iml.com', 'hostname3-eth0.iml.com'],
        sections: ['hostname0..3-eth0.iml.com'],
        expansionHash : {
          'hostname0-eth0.iml.com' : 1,
          'hostname1-eth0.iml.com' : 1,
          'hostname2-eth0.iml.com' : 1,
          'hostname3-eth0.iml.com' : 1
        }
      }
    },
    // Single item with three ranges separated by character
    {
      expression: 'hostname[1,2]-[3-4]-[5,6].iml.com',
      expanded: {
        expansion: ['hostname1-3-5.iml.com', 'hostname1-3-6.iml.com', 'hostname1-4-5.iml.com', 'hostname1-4-6.iml.com',
          'hostname2-3-5.iml.com', 'hostname2-3-6.iml.com', 'hostname2-4-5.iml.com', 'hostname2-4-6.iml.com'],
        sections: ['hostname1..2-3..4-5..6.iml.com'],
        expansionHash : {
          'hostname1-3-5.iml.com' : 1,
          'hostname1-3-6.iml.com' : 1,
          'hostname1-4-5.iml.com' : 1,
          'hostname1-4-6.iml.com' : 1,
          'hostname2-3-5.iml.com' : 1,
          'hostname2-3-6.iml.com' : 1,
          'hostname2-4-5.iml.com' : 1,
          'hostname2-4-6.iml.com' : 1
        }
      }
    },
    // Single item with two ranges and no separation between the ranges
    {
      expression: 'hostname[1,2][3,4].iml.com',
      expanded: {
        expansion: ['hostname13.iml.com', 'hostname14.iml.com', 'hostname23.iml.com', 'hostname24.iml.com'],
        sections: ['hostname1..23..4.iml.com'],
        expansionHash : {
          'hostname13.iml.com' : 1,
          'hostname14.iml.com' : 1,
          'hostname23.iml.com' : 1,
          'hostname24.iml.com' : 1
        }
      }
    },
    // Single item with prefix range starting at 0
    {
      expression: 'test[000-002].localdomain',
      expanded: {
        expansion: ['test000.localdomain', 'test001.localdomain', 'test002.localdomain'],
        sections: ['test000..002.localdomain'],
        expansionHash : {
          'test000.localdomain' : 1,
          'test001.localdomain' : 1,
          'test002.localdomain' : 1
        }
      }
    },
    // Three items in equivalent format in which the difference between ranges is 1. These ranges can be
    // combined.
    {
      expression: 'hostname[2,6,7].iml.com,hostname[10,11-12,2-3,5].iml.com, hostname[15-17].iml.com',
      expanded: {
        expansion: [ 'hostname2.iml.com', 'hostname3.iml.com', 'hostname5.iml.com', 'hostname6.iml.com',
          'hostname7.iml.com', 'hostname10.iml.com', 'hostname11.iml.com', 'hostname12.iml.com',
          'hostname15.iml.com', 'hostname16.iml.com', 'hostname17.iml.com' ],
        sections: [ 'hostname2..3.iml.com', 'hostname5..7.iml.com', 'hostname10..12.iml.com',
          'hostname15..17.iml.com' ],
        expansionHash : {
          'hostname2.iml.com' : 1,
          'hostname3.iml.com' : 1,
          'hostname5.iml.com' : 1,
          'hostname6.iml.com' : 1,
          'hostname7.iml.com' : 1,
          'hostname10.iml.com' : 1,
          'hostname11.iml.com' : 1,
          'hostname12.iml.com' : 1,
          'hostname15.iml.com' : 1,
          'hostname16.iml.com' : 1,
          'hostname17.iml.com' : 1
        }
      }
    },
    // Padding with a single and double digit number
    {
      expression: 'hostname[06-10]',
      expanded: {
        expansion: ['hostname06', 'hostname07', 'hostname08', 'hostname09', 'hostname10'],
        sections: ['hostname06..10'],
        expansionHash : {
          'hostname06' : 1,
          'hostname07' : 1,
          'hostname08' : 1,
          'hostname09' : 1,
          'hostname10' : 1
        }
      }
    },
    // Invalid character in range (snowman)
    {
      expression: 'test[00☃-002].localdomain',
      expanded: {
        errors: ['Range is not in the proper format.']
      }
    },
    // Empty expression
    {
      expression: '',
      expanded: {
        errors: ['Expression cannot be empty.']
      }
    },
    // No separation between comma's
    {
      expression: 'hostname[1,,2].iml.com',
      expanded: {
        errors: ['Range is not in the proper format.']
      }
    },
    // No separation between dashes
    {
      expression: 'hostname[1--2].iml.com',
      expanded: {
        errors: ['Range is not in the proper format.']
      }
    },
    // No separation between dash and comma
    {
      expression: 'hostname[1-,2].iml.com',
      expanded: {
        errors: ['Range is not in the proper format.']
      }
    },
    // No separation between comma and dash
    {
      expression: 'hostname[1,-2].iml.com',
      expanded: {
        errors: ['Range is not in the proper format.']
      }
    },
    // Missing closing brace
    {
      expression: 'hostname[1',
      expanded: {
        errors: ['Expression is invalid']
      }
    },
    // Ending an expression with a comma
    {
      expression: 'hostname[1],',
      expanded: {
        errors: ['Expression is invalid']
      }
    },
    // Beginning and ending prefixes that don't match with two single digit numbers
    {
      expression: 'hostname[01-009]',
      expanded: {
        errors: ['Number of digits must be consistent across padded entries']
      }
    },
    // Having a closing brace before an opening brace
    {
      expression: 'hostname]00[asdf',
      expanded: {
        errors: ['Expression is invalid']
      }
    },
    // Going over cap
    {
      expression: 'hostname[1-50001].iml.com',
      expanded: {
        errors: ['The hostlist cannot contain more than 50000 entries.']
      }
    },
    // Going over cap using multiple ranges in a single expression
    {
      expression: 'hostname[1-25001].iml[1-2].com',
      expanded: {
        errors: ['The hostlist cannot contain more than 50000 entries.']
      }
    },
    // Going over cap using multiple ranges in multiple expressions
    {
      expression: 'hostname[1-20000].iml[1-2].com,host[1-10001].iml[1].com',
      expanded: {
        errors: ['The hostlist cannot contain more than 50000 entries.']
      }
    },
    // Going over cap so far that it could freeze the browser
    {
      expression: 'hostname[1-5000000000000000000000001].iml.com',
      expanded: {
        errors: ['The hostlist cannot contain more than 50000 entries.']
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
