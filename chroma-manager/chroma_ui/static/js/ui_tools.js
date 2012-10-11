//
// ========================================================
// Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
// ========================================================

/*global STATIC_URL */

// Intended to house link builders and tag generators for common elements
var UIHelper = function() {


  // build a tag
  // tag
  // options:
  //    - content : str; stuff to put inside the tag (default: '')
  //                (non-zero length forces close_tag to be true)
  //    - properties : obj; properties to add to the tag (default {})
  //    - close_tag : bool; whether to close the tag or not (default false);
  // NOTE: properties are assumed to have keys that are html safe and the values pre-escaped
  // It is unsafe to pass in properties from external sources
  function build_tag(tag, options) {

    var _options = _.defaults({ close_tag: false }, options || {} );

    var html = '<' + tag;
    if ( _.isObject(_options.properties) ) {
      html += ' ' + _.map(
                        _options.properties,
                        function(value, property) { return property + "='" + value + "'"; }
                      ).join(' ');
    }
    html += '>';

    if ( _.isString(_options.content) && _options.content.length > 0 ) {
      html += _options.content;
      _options.close_tag = true;
    }
    if ( _options.close_tag ) {
      html += '</' + tag + '>';
    }

    return html;
  }

  // build an image tag to a fugue icon
  // name: filename of the icon without file extension
  // data: (optional) an object who's properties will be built into data-X properties
  function fugue_icon(name, properties) {
    var _properties = _.defaults({ 'class': '' }, properties || {}, { src: STATIC_URL + "images/fugue/" + name + ".png" } );
    _properties['class'] =  'fugue_icon' + _properties['class']; // prepend class with fugue_icon
    return build_tag('img', { properties: _properties } );
  }

  // Build an <img> tag based on an INFO/ERROR/WARNING severity string
  function severity_icon(severity) {
    var name = {
        INFO: 'information',
        ERROR: 'exclamation-red',
        WARNING: 'exclamation'
      }[severity];
    return fugue_icon(name, {alt: severity, title: severity});
  }

  // build a help link (help.js)
  // topic: req'd ;html filename of contextual help (without the .html file ext)
  // content: req'd for link_type hover or button; link/button content
  // properties: optional; other html properties you'd like applied to the link
  function _help_link(link_type, topic, content, properties) {
    var _properties = _.defaults({ 'class': '' }, properties || {}, { 'data-topic': topic })
    _properties['class'] = link_type + ' ' + _properties['class'];
    return build_tag('a', { content: content, properties: _properties } );
  }

  // dispatchers to _help_link
  // build a hoverin tooltip over content
  function help_hover(topic,content,properties) {
    return _help_link('help_hover', topic, content, properties);
    // OR return _help_link.apply(['help_hover'].concat([].slice.apply(arguments))) !
  }
  // build a help button with text
  function help_button(topic, content, properties) {
    return _help_link('help_button', topic, content, properties );
  }
  // build a small help button with just ?
  function help_button_small( topic, properties) {
    return _help_link('help_button_small', topic, undefined, properties);
  }

  return {
    build_tag: build_tag,
    fugue_icon: fugue_icon,
    severity_icon: severity_icon,
    help_hover: help_hover,
    help_button: help_button,
    help_button_small: help_button_small
  };

}();
