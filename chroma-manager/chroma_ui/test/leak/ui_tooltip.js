describe('tooltip leaks', function () {
  'use strict';

  beforeEach(module('ui.bootstrap'));

  describe('cleanup', function () {
    it('should not contain any cached references', inject(function ($compile, $timeout, $rootScope) {
      var elmBody, elm, elmScope, tooltipScope;
      var startCacheLength = Object.keys($.cache).length;

      elmBody = angular.element('<div><input tooltip="Hello!" /></div>');
      $compile(elmBody)($rootScope);
      $rootScope.$apply();
      elm = elmBody.find('input');
      elmScope = elm.scope();
      tooltipScope = elmScope.$$childTail;

      function inCache() {
        var match = false;

        angular.forEach(angular.element.cache, function (item) {
          if (item.data && item.data.$scope === tooltipScope) {
            match = true;
          }
        });

        return match;
      }

      expect(inCache()).toBeTruthy();
      elmScope.$destroy();
      elmBody.remove();
      $timeout.flush();

      var endCacheLength = Object.keys($.cache).length;

      expect(inCache()).toBeFalsy();

      expect(startCacheLength).toEqual(endCacheLength);
    }));
  });
});
