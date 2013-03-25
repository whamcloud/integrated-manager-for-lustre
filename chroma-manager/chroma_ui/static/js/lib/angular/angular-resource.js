/**
 * @license AngularJS v1.0.5
 * (c) 2010-2012 Google, Inc. http://angularjs.org
 * License: MIT
 */
(function(window, angular, undefined) {
  'use strict';


  angular.module('ngResource', ['ng']).
    factory('$resource', ['$http', '$parse', function($http, $parse) {
      var DEFAULT_ACTIONS = {
        'get':    {method:'GET'},
        'save':   {method:'POST'},
        'query':  {method:'GET', isArray:true},
        'remove': {method:'DELETE'},
        'delete': {method:'DELETE'}
      };
      var noop = angular.noop,
        forEach = angular.forEach,
        extend = angular.extend,
        copy = angular.copy,
        isFunction = angular.isFunction,
        getter = function(obj, path) {
          return $parse(path)(obj);
        };

      /**
       * We need our custom method because encodeURIComponent is too aggressive and doesn't follow
       * http://www.ietf.org/rfc/rfc3986.txt with regards to the character set (pchar) allowed in path
       * segments:
       *    segment       = *pchar
       *    pchar         = unreserved / pct-encoded / sub-delims / ":" / "@"
       *    pct-encoded   = "%" HEXDIG HEXDIG
       *    unreserved    = ALPHA / DIGIT / "-" / "." / "_" / "~"
       *    sub-delims    = "!" / "$" / "&" / "'" / "(" / ")"
       *                     / "*" / "+" / "," / ";" / "="
       */
      function encodeUriSegment(val) {
        return encodeUriQuery(val, true).
          replace(/%26/gi, '&').
          replace(/%3D/gi, '=').
          replace(/%2B/gi, '+');
      }


      /**
       * This method is intended for encoding *key* or *value* parts of query component. We need a custom
       * method becuase encodeURIComponent is too agressive and encodes stuff that doesn't have to be
       * encoded per http://tools.ietf.org/html/rfc3986:
       *    query       = *( pchar / "/" / "?" )
       *    pchar         = unreserved / pct-encoded / sub-delims / ":" / "@"
       *    unreserved    = ALPHA / DIGIT / "-" / "." / "_" / "~"
       *    pct-encoded   = "%" HEXDIG HEXDIG
       *    sub-delims    = "!" / "$" / "&" / "'" / "(" / ")"
       *                     / "*" / "+" / "," / ";" / "="
       */
      function encodeUriQuery(val, pctEncodeSpaces) {
        return encodeURIComponent(val).
          replace(/%40/gi, '@').
          replace(/%3A/gi, ':').
          replace(/%24/g, '$').
          replace(/%2C/gi, ',').
          replace((pctEncodeSpaces ? null : /%20/g), '+');
      }

      function Route(template, defaults) {
        this.template = template = template + '#';
        this.defaults = defaults || {};
        var urlParams = this.urlParams = {};
        forEach(template.split(/\W/), function(param){
          if (param && (new RegExp("(^|[^\\\\]):" + param + "\\W").test(template))) {
            urlParams[param] = true;
          }
        });
        this.template = template.replace(/\\:/g, ':');
      }

      Route.prototype = {
        url: function(params) {
          var self = this,
            url = this.template,
            val,
            encodedVal;

          params = params || {};
          forEach(this.urlParams, function(_, urlParam){
            val = params.hasOwnProperty(urlParam) ? params[urlParam] : self.defaults[urlParam];
            if (angular.isDefined(val) && val !== null) {
              encodedVal = encodeUriSegment(val);
              url = url.replace(new RegExp(":" + urlParam + "(\\W)", "g"), encodedVal + "$1");
            } else {
              url = url.replace(new RegExp("(\/?):" + urlParam + "(\\W)", "g"), function(match,
                                                                                         leadingSlashes, tail) {
                if (tail.charAt(0) == '/') {
                  return tail;
                } else {
                  return leadingSlashes + tail;
                }
              });
            }
          });
          url = url.replace(/\/?#$/, '');
          var query = [];

          function encodePair (key, value) {
            if (!self.urlParams[key]) {
              query.push(encodeUriQuery(key) + '=' + encodeUriQuery(value));
            }
          }

          forEach(params, function(value, key){
            if (Array.isArray(value)) {
              value.forEach(function (el) {
                encodePair(key, el);
              });
            } else {
              encodePair(key, value);
            }
          });
          query.sort();
          url = url.replace(/\/*$/, '');
          return url + (query.length ? '?' + query.join('&') : '');
        }
      };


      function ResourceFactory(url, paramDefaults, actions) {
        var route = new Route(url);

        actions = extend({}, DEFAULT_ACTIONS, actions);

        function extractParams(data, actionParams){
          var ids = {};
          actionParams = extend({}, paramDefaults, actionParams);
          forEach(actionParams, function(value, key){
            ids[key] = value.charAt && value.charAt(0) == '@' ? getter(data, value.substr(1)) : value;
          });
          return ids;
        }

        function Resource(value){
          copy(value || {}, this);
        }

        forEach(actions, function(action, name) {
          action.method = angular.uppercase(action.method);
          var hasBody = action.method == 'POST' || action.method == 'PUT' || action.method == 'PATCH';
          Resource[name] = function(a1, a2, a3, a4) {
            var params = {};
            var data;
            var success = noop;
            var error = null;
            switch(arguments.length) {
              case 4:
                error = a4;
                success = a3;
              //fallthrough
              case 3:
              case 2:
                if (isFunction(a2)) {
                  if (isFunction(a1)) {
                    success = a1;
                    error = a2;
                    break;
                  }

                  success = a2;
                  error = a3;
                  //fallthrough
                } else {
                  params = a1;
                  data = a2;
                  success = a3;
                  break;
                }
              case 1:
                if (isFunction(a1)) success = a1;
                else if (hasBody) data = a1;
                else params = a1;
                break;
              case 0: break;
              default:
                throw "Expected between 0-4 arguments [params, data, success, error], got " +
                  arguments.length + " arguments.";
            }

            var value = this instanceof Resource ? this : (action.isArray ? [] : new Resource(data));
            value.__promise = $http({
              method: action.method,
              url: route.url(extend({}, extractParams(data, action.params || {}), params)),
              data: data
            }).then(function(response) {
                var data = response.data;

                if (data) {
                  if (action.isArray) {
                    value.length = 0;

                    forEach(data, function(item) {
                      value.push(new Resource(item));
                    });
                  } else {
                    copy(data, value);
                  }
                }
                (success||noop)(value, response.headers);
              }, error);

            if (angular.isFunction(action.patchValue)) {
              action.patchValue(value);
            }

            return value;
          };


          Resource.prototype['$' + name] = function(a1, a2, a3) {
            var params = extractParams(this),
              success = noop,
              error;

            switch(arguments.length) {
              case 3: params = a1; success = a2; error = a3; break;
              case 2:
              case 1:
                if (isFunction(a1)) {
                  success = a1;
                  error = a2;
                } else {
                  params = a1;
                  success = a2 || noop;
                }
              case 0: break;
              default:
                throw "Expected between 1-3 arguments [params, success, error], got " +
                  arguments.length + " arguments.";
            }
            var data = hasBody ? this : undefined;
            Resource[name].call(this, params, data, success, error);
          };
        });

        Resource.bind = function(additionalParamDefaults){
          return ResourceFactory(url, extend({}, paramDefaults, additionalParamDefaults), actions);
        };

        return Resource;
      }

      return ResourceFactory;
    }]);

})(window, window.angular);
