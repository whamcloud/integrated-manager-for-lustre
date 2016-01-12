mock.register('baseModel', function () {
  'use strict';

  var obj = {
    BaseModel: function () {}
  };

  spyOn(obj, 'BaseModel');

  return jasmine.createSpy('baseModel').and.returnValue(obj.BaseModel);
});
