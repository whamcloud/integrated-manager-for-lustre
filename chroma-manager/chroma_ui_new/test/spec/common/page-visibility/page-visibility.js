describe('The Page visibility service', function () {
  'use strict';

  var pageVisibility, document;

  var prefixes = ['webkit', 'moz', 'ms'];

  beforeEach(module('pageVisibility'));

  mock.factory(function $document() {
    return [{
      addEventListener: jasmine.createSpy('document.addEventListener'),
      removeEventListener: jasmine.createSpy('document.removeEventListener')
    }];
  });

  mock.beforeEach('$document');

  beforeEach(inject(function ($document) {
    document = $document[0];
  }));

  prefixes.forEach(function testPrefix (prefix) {
    var eventName, spy, deregister;

    describe('when the browser is ' + prefix, function () {
      beforeEach(function () {
        document[prefix + 'Hidden'] = false;

        eventName = prefix + 'visibilitychange';

        spy = jasmine.createSpy('spy');
      });

      beforeEach(inject(function (_pageVisibility_) {
        pageVisibility = _pageVisibility_;

        deregister = pageVisibility.onChange(spy);
      }));

      it('should register visibilitychange with the correct prefix', function () {
        expect(document.addEventListener).toHaveBeenCalledOnceWith(eventName, jasmine.any(Function));
      });

      it('should call the event handler with the current hidden state', function () {
        var cb = document.addEventListener.mostRecentCall.args[1];

        cb();

        expect(spy).toHaveBeenCalledOnceWith(false);
      });

      it('onChange should return a deregistration function', function () {
        deregister();

        expect(document.removeEventListener).toHaveBeenCalledOnceWith(eventName, jasmine.any(Function));
      });
    });
  });
});
