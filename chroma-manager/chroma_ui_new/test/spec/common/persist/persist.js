//
// INTEL CONFIDENTIAL
//
// Copyright 2013 Intel Corporation All Rights Reserved.
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


describe('Persist service', function () {
  'use strict';

  var $scope, protocol, persist, $q, expression;

  beforeEach(module('persist'));

  beforeEach(inject(function($rootScope, _persist_, _$q_) {
    persist = _persist_;
    $q = _$q_;

    $scope = $rootScope.$new();

    $scope.foo = { bar: { baz: 'meh' } };
    expression = 'foo.bar';

    protocol = {
      subscribe: jasmine.createSpy('subscribe'),
      process: jasmine.createSpy('process').andCallFake(function (newVal, oldVal, deferred) {
        deferred.resolve(newVal);
      }),
      unsubscribe: jasmine.createSpy('unsubscribe')
    };
  }));

  it('should pass changes to the protocol', function () {
    var instance = persist(protocol),
      newValue = {baz: 'test'};

    instance.assign($scope, expression);

    $scope.$digest();

    instance.setter(newValue);

    $scope.$digest();

    expect(protocol.process).toHaveBeenCalledWith(newValue, {baz: 'meh'}, jasmine.any(Object));
  });

  describe('model middleware', function () {
    it('should accept arbitrary middlewares', function () {
      var newValue = {baz: 'fooBar'},
        instance = persist(protocol, {
        modelChange: function (newVal, oldVal, deferred) {
          deferred.resolve(newValue);
        }
      });

      instance.assign($scope, expression);

      $scope.$digest();

      instance.setter({baz: 'not used'});

      $scope.$digest();

      expect(protocol.process).toHaveBeenCalledWith(newValue, {baz: 'meh'}, jasmine.any(Object));
    });
  });

  describe('protocol middleware', function () {
    it('should accept arbitrary middlewares', function () {
      var middleware = jasmine.createSpy('middleware').andCallFake(function (newVal, oldVal, deferred) {
        deferred.resolve(newValue);
      }),
        newValue = {baz: 'hello from protocol!'},
        instance = persist(protocol, { protocolChange: middleware });

      instance.assign($scope, expression);

      $scope.$digest();

      var deferred = $q.defer();

      instance.protocolChange(deferred.promise);

      deferred.resolve({baz: 'not used'});

      $scope.$digest();

      expect(middleware).toHaveBeenCalledWith({baz: 'not used'}, undefined, jasmine.any(Object));

      $scope.$digest();

      expect(instance.getter()).toEqual(newValue);
    });
  });

  describe('cleanup', function () {
    var instance;

    beforeEach(function () {
      instance = persist(protocol);
      instance.assign($scope, 'foo.bar');
    });

    it('should unbind the scope on $destroy', function () {
      $scope.$destroy();
      expect(protocol.unsubscribe).toHaveBeenCalled();
    });

    it('should unbind when called', function () {
      instance.unassign();
      expect(protocol.unsubscribe).toHaveBeenCalled();
      expect(instance.getter).toBeFalsy();
      expect(instance.setter).toBeFalsy();
    });
  });
});
