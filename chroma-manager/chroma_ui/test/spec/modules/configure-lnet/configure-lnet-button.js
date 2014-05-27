describe('configure LNet button', function () {
  'use strict';

  var $scope, $dialog;

  beforeEach(module('configureLnet'));

  mock.beforeEach('$dialog');

  beforeEach(inject(function ($controller, $rootScope, _$dialog_) {
    $scope = $rootScope.$new();
    $dialog = _$dialog_;

    $controller('ConfigureLnetButtonCtrl', {$scope: $scope});
  }));

  it('should create the dialog on init', function () {
    expect($dialog.dialog).toHaveBeenCalledOnceWith({
      keyboard : false,
      backdropClick : false,
      resolve: {
        hostInfo: jasmine.any(Function)
      }
    });
  });

  it('should open a dialog on configure', function () {
    $scope.configure();

    expect($dialog.dialog.spy.open).toHaveBeenCalledOnce();
  });
});
