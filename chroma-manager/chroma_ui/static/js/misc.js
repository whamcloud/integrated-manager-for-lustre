//
// INTEL CONFIDENTIAL
//
// Copyright 2013-2014 Intel Corporation All Rights Reserved.
//
// The source code contained or described herein and all documents related
// to the source code ("Material") are owned by Intel Corporation or its
// suppliers or licensors. Title to the Material remains with Intel Corporation
// or its suppliers and licensors. The Material contains trade secrets and
// proprietary and confidential information of Intel or its suppliers and
// licensors. The Material is protected by worldwide copyright and trade secret
// laws and treaty provisions. No part of the Material may be used, copied,
// reproduced, modified, published, uploaded, posted, transmitted, distributed,
// or disclosed in any way without Intel's prior express written permission.
//
// No license under any patent, copyright, trade secret or other intellectual
// property right is granted to or conferred upon you by disclosure or delivery
// of the Materials, either expressly, by implication, inducement, estoppel or
// otherwise. Any license under such intellectual property rights must be
// express and approved by Intel in writing.



/* returns a floating point nubmer with fixed precision */
function formatNumberPrecision(number, precision) {

    var n = number;
    var s = n < 0 ? "-" : "";
    var p = isNaN(precision = Math.abs(precision)) ? 3 : precision;
    return s +  parseFloat(Math.abs(+n || 0).toPrecision(p));
}

/* precision is how many significant digits to keep */
function formatBytes(bytes, precision) {
  if (bytes == null || bytes == undefined) {
    return bytes;
  }
  if (precision == undefined) {
    precision = 3;
  }

  if (bytes > Math.pow(2, 40)) {
    bytes = formatNumberPrecision(bytes / Math.pow(2, 40), precision) + 'TB';
  } else {
    if (bytes >= 1073741824) {
      bytes = formatNumberPrecision(bytes / 1073741824, precision) + 'GB';
    } else {
      if (bytes >= 1048576) {
        bytes = formatNumberPrecision(bytes / 1048576, precision) + 'MB';
      } else {
        if (bytes >= 1024) {
          bytes = formatNumberPrecision(bytes / 1024, precision) + 'KB';
        } else {
          bytes = formatNumberPrecision(bytes, precision) + 'b';
        }
      }
    }
  }
  return bytes;
}

function formatKBytes(kbytes, precision) {
  return formatBytes(kbytes * 1024, precision);
}

function formatBigNumber(number, precision) {
  if (number == null || number == undefined) {
    return number;
  }
  if (precision == undefined) {
    precision = 3;
  }

	if (number >= 1000000000) {
	     number = formatNumberPrecision(number / 1000000000, precision) + 'B';
	} else { 
		if (number >= 1000000) {
     		number = formatNumberPrecision(number / 1000000, precision) + 'M';
   	} else { 
			if (number >= 1000) {
    		number = formatNumberPrecision(number / 1000, precision) + 'k';
  		}
 		}
	}
  return number;
}

/* https://docs.djangoproject.com/en/1.2/ref/contrib/csrf/#csrf-ajax */
$(document).ajaxSend(function(event, xhr, settings) {
    function getCookie(name) {
        var cookieValue = null;
        if (document.cookie && document.cookie != '') {
            var cookies = document.cookie.split(';');
            for (var i = 0; i < cookies.length; i++) {
                var cookie = jQuery.trim(cookies[i]);
                // Does this cookie string begin with the name we want?
                if (cookie.substring(0, name.length + 1) == (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    function sameOrigin(url) {
        // url could be relative or scheme relative or absolute
        var host = document.location.host; // host + port
        var protocol = document.location.protocol;
        var sr_origin = '//' + host;
        var origin = protocol + sr_origin;
        // Allow absolute or scheme relative URLs to same origin
        return (url == origin || url.slice(0, origin.length + 1) == origin + '/') ||
            (url == sr_origin || url.slice(0, sr_origin.length + 1) == sr_origin + '/') ||
            // or any other URL that isn't scheme relative or absolute i.e relative.
            !(/^(\/\/|http:|https:).*/.test(url));
    }
    function safeMethod(method) {
        return (/^(GET|HEAD|OPTIONS|TRACE)$/.test(method));
    }

    if (!safeMethod(settings.type) && sameOrigin(settings.url)) {
        xhr.setRequestHeader("X-CSRFToken", getCookie('csrftoken'));
    }
});

