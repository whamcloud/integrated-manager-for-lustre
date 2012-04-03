

$(document).ready(function() {
  $('#transition_confirmation_dialog').dialog({autoOpen: false, maxHeight: 400, maxWidth: 800, width: 'auto', height: 'auto'});
});

stateTransition = function (url, state)
{
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
        console.log(consequence_info)
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
     $('#transition_confirmation_dialog').html(confirmation_markup);
     $('#transition_confirmation_dialog').dialog('option', 'buttons', {
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
     });
     $('#transition_confirmation_dialog').dialog('open');
    } else {
      Api.put(url, {state: state})
    }
  });
}


function stateTransitionButtons(stateful_object)
{
  var id = stateful_object.id;
  var ct = stateful_object.content_type_id;
  var available_transitions = stateful_object.available_transitions;

  var ops_action="";
  var action="<span class='transition_buttons' data-resource_uri='" + stateful_object.resource_uri + "'>";
  var button_class = "ui-state-default ui-corner-all";
  $.each(available_transitions, function(i, transition)
  {
    var function_name = "stateTransition(\"" + stateful_object.resource_uri + "\", \"" + transition.state + "\")"
    ops_action = "<button" + " onclick='"+ function_name + "'>" + transition.verb + "</button>&nbsp;";
    action += ops_action;
  });
  action += "</span>"
  return action;
}