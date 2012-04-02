
var ApiCache = function(){
  var Filesystem = Backbone.Model.extend({
    urlRoot: "/api/filesystem/"
  });

  var FilesystemCollection = Backbone.Collection.extend({
    model: Filesystem,
    url: "/api/filesystem/"
  })

  var Target = Backbone.Model.extend({
    urlRoot: "/api/filesystem/"
  });

  var TargetCollection = Backbone.Collection.extend({
    model: Target,
    url: "/api/target/"
  })

  var filesystem_collection = new FilesystemCollection()
  var target_collection = new TargetCollection()

  var init = function(params) {
    params = params || {};

    var collections = [filesystem_collection, target_collection]
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
  }

  return {
    filesystem: filesystem_collection,
    target: target_collection,
    init: init
  }
}();
