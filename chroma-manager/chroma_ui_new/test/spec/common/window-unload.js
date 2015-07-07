describe('window unload', function () {
  'use strict';

  beforeEach(module('windowUnload', '$windowMock'));

  var $window, windowUnload;

  beforeEach(inject(function (_$window_, _windowUnload_) {
    $window = _$window_;
    windowUnload = _windowUnload_;
  }));

  it('should register a beforeunload listener to $window', function () {
    expect($window.addEventListener).toHaveBeenCalledOnceWith('beforeunload', jasmine.any(Function));
  });

  it('should return an object representing unload state', function () {
    expect(windowUnload).toEqual({unloading: false});
  });

  it('should change the unloading state once beforeunload has fired', function () {
    var beforeUnload = $window.addEventListener.mostRecentCall.args[1];

    beforeUnload();

    expect(windowUnload).toEqual({unloading: true});
  });
});
