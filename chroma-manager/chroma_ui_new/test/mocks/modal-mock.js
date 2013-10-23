mock.register({name: '$modal', type: 'provider', setup: function () {
  'use strict';

  this.$get = function ($q) {
    var $modal = {
      instances: {}
    };

    $modal.open = jasmine.createSpy('open').andCallFake(function (options) {
      var modalResult = $q.defer();

      var modalInstance = {
        close: jasmine.createSpy('close').andCallFake(function (result) {
          modalResult.resolve(result);
        }),
        dismiss: jasmine.createSpy('dismiss').andCallFake(function (reason) {
          modalResult.reject(reason);
        }),
        result: modalResult.promise,
        opened: $q.defer().resolve(true)
      };

      $modal.instances[options.templateUrl || options.windowClass] = modalInstance;

      return modalInstance;
    });

    return $modal;
  };
}});
