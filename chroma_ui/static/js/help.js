
function help_elements() {
  function help_qtip(element, click) {
    var event;
    if (click) {
      event = 'click';
    } else {
      event = 'mouseenter';
    }

    element.qtip({
      content: {
        text: 'Loading...',
        ajax: {
          url: STATIC_URL + "contextual/" + element.data('topic') + ".html",
          type: "GET",
          data: {}
        }
      },
      show: {
        event: event
      }
    });
  }

  $('a.help_hover').each(function() {
    var el = $(this);
    if (!el.data('qtip')) {
      help_qtip(el, false);
    }
  });

  $('a.help_button').each(function() {
    var el = $(this);
    if (!el.data('qtip')) {
      el.button({icons: {primary: 'ui-icon-help'}});
      help_qtip(el, true);
    }
  });

  $('a.help_button_small').each(function() {
    var el = $(this);
    if (!el.data('qtip')) {
      el.css('padding', '0px')
      el.css('width', '24px')
      el.css('height', '24px')
      el.button({icons: {primary: 'ui-icon-help'}});
      el.find('.ui-icon').css('margin-left', '-3px');
      help_qtip(el, true);
    }
  });
}

$(document).ready(help_elements);
$(document).ajaxComplete(help_elements);


/*
 * Examples:
<a class='help_hover' data-topic='test'>My help</a>
<a class='help_button' data-topic='test'>My help</a>
<a class='help_button_small' data-topic='test'></a>
*/
