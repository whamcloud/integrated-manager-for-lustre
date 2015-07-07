describe('model factory', function () {
  'use strict';

  var $httpBackend, $rootScope, modelFactoryProvider, modelFactory, SubTypeSpy, ItemResource, ItemsResource;

  beforeEach(module('modelFactory', {STATIC_URL: '/static'}, function (_modelFactoryProvider_) {
    modelFactoryProvider = _modelFactoryProvider_;
  }));

  beforeEach(inject(function (_modelFactory_, _$httpBackend_, _$rootScope_) {
    modelFactory = _modelFactory_;
    $httpBackend = _$httpBackend_;
    $rootScope = _$rootScope_;

    SubTypeSpy = jasmine.createSpy('SubTypeSpy');

    ItemResource = modelFactory({ url: 'item' });
    ItemsResource = modelFactory({ url: 'items' });

    $httpBackend.whenGET('item/').respond(200, {
      foo: 2,
      subType: {
        bar: 'baz',
        nestedSubType: {
          foo: 'bar'
        }
      }
    });

    $httpBackend.whenGET('items/').respond(200, [{
      foo: 2,
      subType: {
        bar: 'baz'
      }
    }]);
  }));

  afterEach(function() {
    $httpBackend.verifyNoOutstandingExpectation();
    $httpBackend.verifyNoOutstandingRequest();
  });

  it('should throw if a url is not passed', function () {
    expect(modelFactory.bind(null, {})).toThrow();
  });

  it('should allow a url prefix to be set', function () {
    modelFactoryProvider.setUrlPrefix('/api/');

    $httpBackend.expectGET('/api/foo/').respond(200);

    modelFactory({url: 'foo'}).get();

    $httpBackend.flush();
  });

  it('should allow methods to be added to a resource', function () {
    var ItemResource = modelFactory({
      url: 'item'
    });

    ItemResource.prototype.fooPlusTwo = function fooPlusTwo () {
      return this.foo + 2;
    };


    var itemResource = ItemResource.get();

    $httpBackend.flush();
    $rootScope.$digest();

    expect(itemResource.fooPlusTwo()).toEqual(4);
  });

  it('should not overwrite properties on a resource', function () {
    ItemResource.prototype.foo = function foo () {
      return 'uh-oh!';
    };

    var itemResource = ItemResource.get();

    $httpBackend.flush();
    $rootScope.$digest();

    expect(itemResource.foo).toEqual(2);
  });

  it('should populate subtypes on a resource', function () {
    ItemResource.subTypes = {
      subType: SubTypeSpy
    };

    ItemResource.get();

    $httpBackend.flush();
    $rootScope.$digest();

    expect(SubTypeSpy).toHaveBeenCalledWith({
      bar: 'baz',
      nestedSubType: {
        foo: 'bar'
      }
    });
  });

  it('should not populate a subtype on a resource if it does not exist', function () {
    ItemResource.subTypes = {
      baz: SubTypeSpy
    };

    ItemResource.get();

    $httpBackend.flush();
    $rootScope.$digest();

    expect(SubTypeSpy).not.toHaveBeenCalled();
  });

  it('should handle nested subTypes', function () {
    var SubType = modelFactory({url: 'nested'});

    SubType.subTypes = {
      nestedSubType: SubTypeSpy
    };

    ItemResource.subTypes = {
      subType: SubType
    };

    ItemResource.get();

    $httpBackend.flush();
    $rootScope.$digest();

    expect(SubTypeSpy).toHaveBeenCalledWith({ foo: 'bar' });
  });

  it('should add methods to resources in a collection', function () {
    ItemsResource.prototype.fooPlusTwo = function fooPlusTwo () {
      return this.foo + 2;
    };

    var itemsResource = ItemsResource.query();

    $httpBackend.flush();
    $rootScope.$digest();

    expect(itemsResource[0].fooPlusTwo()).toEqual(4);
  });

  it('should not overwrite properties on resources in a collection', function () {
    ItemsResource.prototype.foo = function foo () {
      return 'uh-oh!';
    };

    var itemResource = ItemsResource.query();

    $httpBackend.flush();
    $rootScope.$digest();

    expect(itemResource[0].foo).toEqual(2);
  });

  it('should populate subtypes on resources in a collection', function () {
    ItemsResource.subTypes = {
      subType: SubTypeSpy
    };

    ItemsResource.query();

    $httpBackend.flush();
    $rootScope.$digest();

    expect(SubTypeSpy).toHaveBeenCalledWith({bar: 'baz'});
  });

  it('should not populate a subtype on a resource in a collection if it does not exist', function () {
    ItemsResource.subTypes = { baz: SubTypeSpy };

    ItemsResource.query();

    $httpBackend.flush();
    $rootScope.$digest();

    expect(SubTypeSpy).not.toHaveBeenCalled();
  });

  it('should return new instances between calls', function () {
    var ItemResource1 = modelFactory({ url: 'item' }),
      ItemResource2 = modelFactory({ url: 'item' });

    expect(ItemResource1).not.toBe(ItemResource2);
  });
});
