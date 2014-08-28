describe('duration picker', function () {
  'use strict';

  var template, $scope, changeDurationButton, popover,
    updateButton, dropdownButton, dropdownMenu, currentDuration, input, DURATIONS;

  beforeEach(module('charts', 'filters', 'templates'));

  beforeEach(inject(function ($templateCache, $rootScope, $compile, _DURATIONS_) {
    DURATIONS = _DURATIONS_;

    template = angular.element($templateCache.get('duration-picker.html'));

    $scope = $rootScope.$new();
    $scope.onUpdate = jasmine.createSpy('onUpdate');
    $scope.startUnit = DURATIONS.MINUTES;
    $scope.startSize = 10;

    $compile(template)($scope);

    $scope.$digest();

    changeDurationButton = template.find('.activate-popover');
    updateButton = template.find('.btn-success');
    dropdownButton = template.find('.dropdown-toggle');
    popover = template.find('.popover');
    input = template.find('input');
    dropdownMenu = template.find('.dropdown-menu');
    currentDuration = template.find('small');
  }));

  it('should display the currently selected duration', function () {
    var duration = currentDuration.html();

    expect(duration).toEqual('Viewing 10 minutes ago.');
  });

  it('should open the popover when the change duration button is clicked', function () {
    changeDurationButton.click();

    expect(popover).toHaveClass('in');
  });

  it('should default to minutes', function () {
    changeDurationButton.click();

    dropdownButton.click();

    var minutes = _.capitalize(DURATIONS.MINUTES);

    expect(dropdownButton.filter(':contains("%s")'.sprintf(minutes)).length).toEqual(1);
  });

  it('should change the duration unit when the user clicks a dropdown item', function () {
    changeDurationButton.click();

    dropdownButton.click();

    var hours = _.capitalize(DURATIONS.HOURS);

    dropdownMenu.find('a:contains("%s")'.sprintf(hours)).click();

    expect(dropdownButton.filter(':contains("%s")'.sprintf(hours)).length).toEqual(1);
  });

  it('should call the update method when the user clicks update with the correct moments', function () {
    changeDurationButton.click();

    dropdownButton.click();

    updateButton.click();

    var lastCallArgs = $scope.onUpdate.calls.pop().args;

    expect(lastCallArgs).toEqual([DURATIONS.MINUTES, 10]);
  });
});
