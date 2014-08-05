//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2014 Intel Corporation All Rights Reserved.
//
// The source code contained or described herein and all documents related
// to the source code ("Material") are owned by Intel Corporation or its
// suppliers or licensors. Title to the Material remains with Intel Corporation
// or its suppliers and licensors. The Material contains trade secrets and
// proprietary and confidential information of Intel or its suppliers and
// licensors. The Material is protected by worldwide copyright and trade secret
// laws and treaty provisions. No part of the Material may be used, copied,
// reproduced, modified, published, uploaded, posted, transmitted, distributed,
// or disclosed in any way without Intel's prior express written permission.
//
// No license under any patent, copyright, trade secret or other intellectual
// property right is granted to or conferred upon you by disclosure or delivery
// of the Materials, either expressly, by implication, inducement, estoppel or
// otherwise. Any license under such intellectual property rights must be
// express and approved by Intel in writing.


(function () {
  'use strict';

  angular.module('pdsh-parser-module', ['comparators'])
    .factory('pdshParser', ['comparators', function pdshParser (comparators) {
      var errorCollection = {errors: []};
      var expansionCollection = {expansion: []};
      var and = comparators.and;
      var maybe = comparators.maybe;
      var memorizeVal = comparators.memorizeVal;
      var not = comparators.not;
      var isTrue = comparators.isTrue;
      var isFalse = comparators.isFalse;
      var empty = comparators.empty;
      var referenceEqualTo = comparators.referenceEqualTo;
      var greaterThan = comparators.greaterThan;
      var validRangeRegex = /^[0-9]+(?:-[0-9]+)?$/;

      var constants = Object.freeze({
        OPEN_BRACE: '[',
        CLOSING_BRACE: ']',
        RANGE_NOT_PROPER_FORMAT: 'Range is not in the proper format.',
        EXPRESSION_EMPTY: 'Expression cannot be empty.',
        INDEX_OF: 'indexOf',
        LAST_INDEX_OF: 'lastIndexOf'
      });

      /**
       * The pdshParser function returned to the client receives an expression to be parsed.
       * @param {String} expression
       * @return {Array}
       */
      return function pdshParser (expression) {
        maybe(empty(expression), handleEmptyExpression, parseExpression)
        (expression, expansionCollection, errorCollection);

        return (errorCollection.errors.length > 0) ? errorCollection : expansionCollection;
      };

      /**
       * Parses an expression
       * @param {String} expression
       * @param {Object} expansionCollection
       */
      function parseExpression (expression, expansionCollection) {
        expansionCollection.expansion = splitExpressions(expression, isInsideBraces)
          .map(expandExpressions)
          .reduce(flattenArrayOfValues);
      }

      /**
       * Expands the expression list
       * @param {String} expression
       * @returns {Array}
       */
      function expandExpressions (expression) {
        return expandComponents(tokenize(expression));
      }

      /**
       * Adds the expression empty error message to the errors list
       * @param {String} expression
       * @param {Object} expansion
       * @param {Object} errorsCollection
       */
      function handleEmptyExpression (expression, expansion, errorsCollection) {
        errorsCollection.errors.push(constants.EXPRESSION_EMPTY);
      }

      /**
       * Takes a component and expands out the comma delimited string representation. For example:
       * @example
       * //returns ['hostname6.iml.com','hostname7.iml.com']
       * expandComponents(['hostname', '[6,7]', '.iml.com'])
       * @param {Array} components
       * @returns {Array}
       */
      function expandComponents (components) {
        var ranges = [];
        var hostname = components.reduce(_.partial(generateHostNameFormat, ranges));

        // Expand the ranges and save them in expandedRanges
        var expandedRanges = ranges.map(expandRanges);

        return formatString(hostname, expandedRanges);
      }

      /**
       * Generates the host name format
       * @param {Array} ranges
       * @param {String} prev
       * @param {String} current
       * @returns {String}
       */
      function generateHostNameFormat (ranges, prev, current) {
        var newVal = flattenArrayOfValues(prev, current);
        var filteredRanges = [prev, current].filter(range);

        // Concat the filtered ranges onto ranges
        [].push.apply(ranges, filteredRanges);
        // replace the ranges in newVal with a token
        var replaceTextWithTokenS = _.partial(replaceTextWithToken, '%s');
        return filteredRanges.reduce(replaceTextWithTokenS, newVal);
      }

      /**
       * Replaces a specified target with a token in the source string
       * @param {String} token
       * @param {String} source
       * @param {String} target
       * @returns {String}
       */
      function replaceTextWithToken (token, source, target) {
        return source.replace(target, token);
      }

      /**
       * Takes a hostname and an array of ranges and then generates a list of valid host names based on the
       * array of ranges passed in.
       * @param {String} hostname (hostname%s.iml.com)
       * @param {Array} ranges An array of arrays representing the ranges.
       * @param {Number} [id] The current id
       * @returns {Array}
       */
      function formatString (hostname, ranges, id) {
        var curArrayId = (typeof id === 'number' ? id : 0);
        var serverList = [];

        maybe(greaterThan(ranges.length, 0), formatCurrentRange, addItemToArray)
        (serverList, hostname, ranges, curArrayId);

        return serverList;
      }

      /**
       * Formats the current range
       * @param {Array} serverList
       * @param {String} hostname
       * @param {Array} ranges
       * @param {Number} curArrayId
       */
      function formatCurrentRange (serverList, hostname, ranges, curArrayId) {
        var curArray = ranges[curArrayId];
        curArray.forEach(_.partial(computeString, serverList, hostname, ranges, curArrayId));
      }

      /**
       * Builds the host name string given the ranges
       * @param {Array} serverList
       * @param {String} hostname
       * @param {Array} ranges
       * @param {Number} curArrayId
       * @param {String} part
       */
      function computeString (serverList, hostname, ranges, curArrayId, part) {
        var updatedHostName = hostname.replace('%s', part);

        maybe(_.partial(moreRangesAvailable, ranges, curArrayId), processMoreRanges)
        (updatedHostName, ranges, curArrayId, serverList);

        maybe(not(_.partial(moreRangesAvailable, ranges, curArrayId)), addItemToArray)
        (serverList, updatedHostName);
      }

      /**
       * Processes more ranges if more ranges exist
       * @param {String} updatedHostName
       * @param {Array} ranges
       * @param {Number} curArrayId
       * @param {Array} serverList
       */
      function processMoreRanges (updatedHostName, ranges, curArrayId, serverList) {
        var formattedList = formatString(updatedHostName, ranges, curArrayId + 1);
        [].push.apply(serverList, formattedList);
      }

      /**
       * Adds an item to a specified array
       * @param {Array} list
       * @param {*} val
       */
      function addItemToArray (list, val) {
        list.push(val);
      }

      /**
       * Parses a range into an array.
       * @example
       * // returns [0, 1, 2, 3, 4, 7, 9]
       * expandRanges('[0-4,7,9]')
       * @param {String} rangeComponent
       * @returns {Array}
       */
      function expandRanges (rangeComponent) {
        // Remove the beginning and ending brackets
        var componentToParse = rangeComponent.slice(1, -1);
        return componentToParse.split(',')
          .map(parseItem)
          .reduce(flattenArrayOfValues)
          .map(castToNumber);
      }

      /**
       * Casts a value to a number
       * @param {String|Number} val
       * @returns {Number}
       */
      function castToNumber (val) {
        return +val;
      }

      /**
       * Parses an intem
       * @param {String} item
       * @returns {Array}
       */
      function parseItem (item) {
        var isSanitized = isValidRange(item);
        var range = item.split('-');

        var rangeValues = maybe(and(referenceEqualTo(range.length, 2), isTrue(isSanitized)), generateRange, memorizeVal(range))
        (range);
        maybe(isFalse(isSanitized), _.partial(addErrorObject, constants.RANGE_NOT_PROPER_FORMAT))();

        return rangeValues;
      }

      /**
       * Generates an array containing all of the numbers specified in the range (inclusive)
       * @param {String} range
       * @returns {Array}
       */
      function generateRange (range) {
        return _.range(range[0], +range[1] + 1);
      }

      /**
       * An expression may be comma delimited. We can identify expressions by looking for
       * commas. However, it's a bit more complicated than this. We need to identify comma's that
       * separate our expressions. For example:
       * @example
       * vbox[10,11-12,2-3,5],vbox.com
       * There are two expressions here:
       * 1. vbox[10,11-12,2-3,5]
       * 2. vbox.com
       * Therefore, we need to apply a simple rule: For every comma identified, it must not be
       * surrounded by brackets.
       * @param {String} expression
       * @param {Function} isInsideBraces
       * @returns {Array}
       */
      function splitExpressions (expression, isInsideBraces) {
        var expressions = [];
        // Split the expression by commas
        var curLoc = expression.indexOf(',');
        // remove all white space
        expression = expression.replace(/ /g, '');

        return maybe(referenceEqualTo(curLoc, -1), addExpressionToExpressionList,
          lookForMoreExpressionsToSplit)
        (expressions, expression, curLoc, isInsideBraces);
      }

      /**
       * Adds an expression to the expressions array and returns the expressions array
       * @param {Array} expressions
       * @param {String} expression
       * @returns {Array}
       */
      function addExpressionToExpressionList (expressions, expression) {
        expressions.push(expression);
        return expressions;
      }

      /**
       * Looks for more expressions to split
       * @param {Array} expressions
       * @param {String} expression
       * @param {Number} curLoc
       * @param {Function} isInsideBraces
       * @returns {Array}
       */
      function lookForMoreExpressionsToSplit (expressions, expression, curLoc, isInsideBraces) {
        var ruleApplied;
        while (curLoc !== -1 && !ruleApplied) {
          // Apply the rule at the current comma location
          ruleApplied = maybe(isTrue(isInsideBraces(expression, curLoc)),
            addSplitExpression, memorizeVal(false))
          (expressions, expression, curLoc, isInsideBraces);

          curLoc = expression.indexOf(',', curLoc + 1);
        }

        // There may be a final expression like this: hostname[15,17].iml.com
        // In this case, there is no separation of expressions but the if check above would not evaluate to
        // true because there is a comma in this expression; it just isn't separating multiple expressions.
        // Therefore, we need to add this to the list of expressions because it is the final expression.
        maybe(and(referenceEqualTo(expressions.length, 0),
          greaterThan(expression.length, 0)), addExpressionToExpressionList)
        (expressions, expression);

        return expressions;
      }

      /**
       * Adds the split expression to the expressions array
       * @param {Array} expressions
       * @param {String} expression
       * @param {Number} curLoc
       * @param {Function} isInsideBraces
       * @returns {Boolean}
       */
      function addSplitExpression (expressions, expression, curLoc, isInsideBraces) {
        expressions.push(expression.substring(0, curLoc));

        // call split expressions and concat the resulting array onto the expressions list
        [].push.apply(expressions, splitExpressions(expression.slice(curLoc + 1),
          isInsideBraces));

        return true;
      }

      /**
       * Indicates if the location specified is inside braces
       * @param {String} expression The expression
       * @param {Number} loc The subject location in the expression in which the rule is being applied
       * @returns {Boolean}
       */
      function isInsideBraces (expression, loc) {
        // Check the left and right braces to determine if the location is between braces
        var leftSide = expression.substr(0, loc);
        var rightSide = expression.substr(loc + 1);

        return hasBrace(constants.LAST_INDEX_OF, leftSide) && hasBrace(constants.INDEX_OF, rightSide);
      }

      /**
       * HOF that checks if the the specified side has a brace according to the rules below:
       * 1. hasLeftBrace - Is there a brace to the left of this location in which an open brace is NOT closer in distance, or
       * is there no closing brace to the left at all?
       * 2. hasRightBrace - Is there a brace to the right of this location in which a closing brace is NOT closer in distance,
       * or is there no open brace to the right at all?
       * @param {String} indexMethod
       * @param {String} sideString The string in which a search will be performed for the brace.
       * @returns {Boolean}
       */
      function hasBrace (indexMethod, sideString) {
        var closestClosingBrace = sideString[indexMethod](constants.CLOSING_BRACE);
        var closestOpeningBrace = sideString[indexMethod](constants.OPEN_BRACE);

        return ((closestClosingBrace === -1 && closestOpeningBrace === -1) ||
          (closestOpeningBrace < closestClosingBrace));
      }

      /**
       * A recursive algorithm that splits the expression into components.
       * @param {String} expression
       * @returns {Array}
       */
      function tokenize (expression) {
        var tokens = [];
        maybe(and(not(empty(expression)),
          not(isRange(expression))), processNonRanges, addTokenToList(constants.CLOSING_BRACE, 1))
        (tokens, expression);
        return tokens;
      }

      /**
       * Processes expressions without a range
       * @param {Array} tokens
       * @param {String} expression
       */
      function processNonRanges (tokens, expression) {
        maybe(_.partial(rangeExists, expression), addTokenToList(constants.OPEN_BRACE, 0), addItemToArray)
        (tokens, expression);
      }

      /**
       * Adds a token to the tokens list
       * @param {String} key
       * @param {Number} addToIndex
       * @returns {Function}
       */
      function addTokenToList (key, addToIndex) {
        return function innerAddTokenToList (tokens, expression) {
          // We've hit a range. Create an array of values.
          var index = expression.indexOf(key);
          tokens.push(expression.substring(0, index + addToIndex));
          [].push.apply(tokens, tokenize(expression.slice(index + addToIndex)));
        };
      }

      /**
       * Adds an error message to the errors object
       * @param {String} msg
       */
      function addErrorObject (msg) {
        errorCollection.errors.push(msg);
      }

      /**
       * Takes multiple arrays and flattens them into one
       * @param {Array} prev
       * @param {Array} current
       * @returns {Array}
       */
      function flattenArrayOfValues (prev, current) {
        return prev.concat(current);
      }

      /**
       * Predicate indicating if there are more ranges available
       * @param {Array} ranges
       * @param {Number} curArrayId
       * @returns {Boolean}
       */
      function moreRangesAvailable (ranges, curArrayId) {
        return curArrayId + 1 < ranges.length;
      }

      /**
       * Runs a regular expression against a range string. ex. 6-10
       * @param {String} item
       * @returns {Boolean}
       */
      function isValidRange (item) {
        return validRangeRegex.test(item);
      }

      /**
       * Checks if a range is present in an expression
       * @param {String} e The expression
       * @returns {Boolean}
       */
      function rangeExists (e) {
        return e.indexOf(constants.OPEN_BRACE) > -1;
      }

      /**
       * Predicate to indicate if the first character of the expression being passed in indicates a range.
       * @param {String} e The expression
       * @returns {Function}
       */
      function isRange (e) {
        return _.partial(range, e);
      }

      /**
       * Indicates if the first character in the expression is the start of a range
       * @param {String} e The expression passed in
       * @returns {Boolean}
       */
      function range (e) {
        return e[0] === constants.OPEN_BRACE;
      }
    }]);
}());
