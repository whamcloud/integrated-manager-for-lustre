//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================


var ApiCache = function(){
  var Filesystem = Backbone.Model.extend({
    urlRoot: "/api/filesystem/"
  });

  var FilesystemCollection = Backbone.Collection.extend({
    model: Filesystem,
    url: "/api/filesystem/"
  });

  var Target = Backbone.Model.extend({
    urlRoot: "/api/filesystem/"
  });

  var TargetCollection = Backbone.Collection.extend({
    model: Target,
    url: "/api/target/"
  });

  var collections = {
    'filesystem': new FilesystemCollection(),
    'target': new TargetCollection()
  };

  var outstanding_requests = {
    'filesystem': [],
    'target': []
  };

  var init = function(params) {
    params = params || {};

    var init_counter = 0;
    _.each(collections, function(collection) {
      collection.fetch({success: function() {
        init_counter = init_counter + 1;
        if (init_counter == collections.length) {
          if (params.success) {
            params.success();
          }
        }
      }});
    });
  };

  function get(obj_type, obj_id) {
    var collection = collections[obj_type];

    var object = collection.get(obj_id);
    if (!object) {
      if (_.include(outstanding_requests[obj_type], obj_id)) {
        return null;
      } else {
        outstanding_requests[obj_type].push(obj_id);
        collection.fetch({
            add:true,
            data:{id:obj_id},
            success:function () {
              outstanding_requests[obj_type] = _.reject(outstanding_requests[obj_type], function (x) {return x == obj_id;});
            }
        });
      }
    }
    return object;
  }

  return {
    get: get,
    init: init
  }
}();
