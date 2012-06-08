//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================


var ContextualHelp = function(){

  var loaded_snippets = {}; //container for loaded snippets as some are reused
  var compiled_snippet_template = _.template("<div class='ui-helper-clearfix ui-state-<%= state%> ui-corner-all'><div class='contextual_help_icon'><span class='ui-icon ui-icon-<%= icon %>'></span></div><div class='contextual_help'><%= content %></div></div>");

  function contexual_help_link(topic) {
    return STATIC_URL + "contextual/" + topic + ".html";
  }

  function set_default(value, default_value) {
    return ( _.isUndefined(value) ? default_value : value );
  }

  function populate_snippet(container) {
    // skip if no topic
    var topic = $(container).data('topic');
    if (_.isUndefined(topic)) {
      return true;
    }

    var icon = set_default($(container).data('icon'),'info');

    var state = set_default($(container).data('state'),'highlight');

    // if we've already retrieved this one, just pull it from memory
    if (_.has(loaded_snippets,topic)) {
      $(container).html(compiled_snippet_template({ content: loaded_snippets[topic], icon: icon, state: state}));
      return true;
    }

    //otherwise we have to get it
    $.get(contexual_help_link(topic), data = undefined, success = function(topic_html) {
      loaded_snippets[topic] = topic_html;
      $(container).removeClass('help_loader')
        .addClass('help_loaded')
        .html(compiled_snippet_template({ content: topic_html, icon: icon, state: state}));
    });
    return true;
  }

  function load_snippets(parent_selector, snippet_selector) {

    var selector = set_default(snippet_selector,'div.help_loader');
    var snippets;
    if (_.isElement(parent_selector) || _.isString(parent_selector) ) {
      snippets = $(parent_selector).find(selector);
    }
    else {
      snippets = $(selector);
    }

    snippets.each(function() { populate_snippet(this); });

  }

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
            url: contextual_help_link(element.data('topic')),
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
        el.css({ padding: '0px', width: '24px', height: '24px'})
          .button({icons: {primary: 'ui-icon-help'}})
          .find('.ui-icon').css('margin-left', '-3px');
        help_qtip(el, true);
      }
    });
  }

  function init() {
    help_elements();
    $(document).ajaxComplete(help_elements);
  }

  return {
    init: init,
    load_snippets: load_snippets
  };
}();



/*
 * Examples:
<a class='help_hover' data-topic='test'>My help</a>
<a class='help_button' data-topic='test'>My help</a>
<a class='help_button_small' data-topic='test'></a>
<div class='help_loader' data-topic='_advanced_settings' data-icon='info' data-state='highlight|error' />
  - data-icon (optional) can be any valid icon from jquery ui
    reference: http://jqueryui.com/themeroller/ (at the bottom; hover over for name)
    default: info
  - data-state (optional) should be any one of "highlight", "error"
    default: highlight
*/
