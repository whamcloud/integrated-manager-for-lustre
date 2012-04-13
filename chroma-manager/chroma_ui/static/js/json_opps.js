
stateTransition = function ()
{
  console.log(this);
  var url = $(this).data('resource_uri');
  var state = $(this).data('state');

  Api.put(url, {dry_run: true, state: state}, 
  success_callback = function(data)  
  {
    var requires_confirmation = false;
    var confirmation_markup;

    if (data.transition_job == null) {
      // A no-op
      return;
    } else if (data.transition_job.confirmation_prompt) {
      requires_confirmation = true;
      confirmation_markup = "<p><strong>" + data.transition_job.confirmation_prompt + "</strong></p><p>Are you sure?</p>";
    } else if (data.dependency_jobs.length > 0) {
      confirmation_markup = "<p>This action has the following consequences:</p><ul>";
      requires_confirmation = data.transition_job.requires_confirmation;

      $.each(data.dependency_jobs, function(i, consequence_info) {
        confirmation_markup += "<li>" + consequence_info.description + "</li>";

        if (consequence_info.requires_confirmation) {
          requires_confirmation = true;
        }
      });
      confirmation_markup += "</ul>"
    } else {
      requires_confirmation = data.transition_job.requires_confirmation;
      confirmation_markup = "<p><strong>" + data.transition_job.description + "</strong></p><p>Are you sure?</p>";
    }

    if (requires_confirmation) {
      var markup = "<div style='overflow-y: auto; max-height: 700px;' id='transition_confirmation_dialog'>" + confirmation_markup + "</div>";
      $(markup).dialog({'buttons': {
        'Cancel': function() {$(this).dialog('close');},
        'Confirm':
        {
            text: "Confirm",
            id: "transition_confirm_button",
            click: function(){
              var dialog = $(this);
              Api.put(url, {state: state}, success_callback = function() {
                dialog.dialog('close');
              })
            }
        }
      }});
    } else {
      Api.put(url, {state: state})
    }
  });
};