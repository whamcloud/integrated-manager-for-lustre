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
    urlRoot: "/api/target/"
  });

  var TargetCollection = Backbone.Collection.extend({
    model: Target,
    url: "/api/target/"
  });

  var Server = Backbone.Model.extend({
    urlRoot: "/api/host/"
  });

  var ServerCollection = Backbone.Collection.extend({
    model: Server,
    url: "/api/host/"
  });


  var collections = {
    'filesystem': new FilesystemCollection(),
    'target': new TargetCollection(),
    'server': new ServerCollection()
  };

  var outstanding_requests = {
    'filesystem': [],
    'target': [],
    'server': []
  };


  var initialized = false;
  var init = function(params) {
    params = params || {};

    var init_counter = 0;
    _.each(collections, function(collection) {
      collection.fetch({success: function() {
        init_counter = init_counter + 1;
        if (init_counter == _.size(collections)) {
          initialized = true;
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
      if (!initialized || _.include(outstanding_requests[obj_type], obj_id)) {
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

  function list(obj_type) {
    var collection = collections[obj_type];
    return collection.toJSON();
  }

  return {
    get: get,
    list: list,
    init: init
  }
}();
