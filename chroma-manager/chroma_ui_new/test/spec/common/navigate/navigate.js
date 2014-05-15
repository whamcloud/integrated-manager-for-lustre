describe('navigate', function () {
  'use strict';

  var $window, navigate, UI_ROOT;

  beforeEach(module('navigate', '$windowMock', {UI_ROOT: '/root/of/app/'}));

  beforeEach(inject(function (_navigate_, _$window_, _UI_ROOT_) {
    $window = _$window_;
    navigate = _navigate_;
    UI_ROOT = _UI_ROOT_;
  }));

  it('should accept no arguments', function () {
    navigate();

    expect($window.location.__hrefSpy__).toHaveBeenCalledWith(UI_ROOT);
  });

  it('should concatenate the part with the ui root', function () {
    var part = 'foo';

    navigate(part);

    expect($window.location.__hrefSpy__).toHaveBeenCalledWith(UI_ROOT + part);
  });
});
