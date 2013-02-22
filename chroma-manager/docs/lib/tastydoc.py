
# This script extracted from https://github.com/socialize/django-tastypie/commit/6a98aa4ff344105f8b5090a2d4f2d407bccae089
# Inheriting django-tastypie LICENSE for this file only
# Copyright (c) 2010, Daniel Lindsley
# All rights reserved.

# The following notice applies to this file only, and has no bearing
# on other material in the package which contains the file.

# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
    # * Redistributions of source code must retain the above copyright
    # notice, this list of conditions and the following disclaimer.
    # * Redistributions in binary form must reproduce the above copyright
    # notice, this list of conditions and the following disclaimer in the
    # documentation and/or other materials provided with the distribution.
    # * Neither the name of the tastypie nor the
    # names of its contributors may be used to endorse or promote products
    # derived from this software without specific prior written permission.

# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL tastypie BE LIABLE FOR ANY
# DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
# ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from django.http import HttpRequest
#from docutils.parsers.rst import Parser
#from docutils.core import Publisher
from docutils.core import publish_doctree
from django.template import Context, Template
from sphinx.util.compat import Directive
import os
import json


def setup(app):
    app.add_directive('tastydoc', TastyDirective)

import tastypie


class TastyDirective(Directive):
    # this enables content in the directive
    has_content = True

    def run(self):
        module_parts = self.content[0].split(".")
        module = ".".join(module_parts[0:len(module_parts) - 1])
        member = module_parts[len(module_parts) - 1]

        api_module = __import__(module, fromlist = ['a'])
        api = api_module.__dict__[member]

        #parser = Parser()
        #publisher = Publisher()
        request = HttpRequest()
        top_level_response = api.top_level(request, None)
        top_level_doc = json.loads(top_level_response.content)

        for name in sorted(api._registry.keys()):
            resource_dict = top_level_doc[name]
            resource = api._registry[name]
            resource_dict['schema'] = resource.build_schema()
            resource_dict['schema']['field_list'] = [{'name': field, 'meta': meta} for field, meta in resource_dict['schema']['fields'].items()]
            for field, field_meta in resource_dict['schema']['fields'].items():

                if field == 'id':
                    field_meta['help_text'] = "Integer record identifier, unique for objects of this type"
                elif field == 'content_type_id':
                    field_meta['help_text'] = "Integer type identifier"
                elif field == 'state' and field_meta['help_text'] == tastypie.fields.CharField.help_text:
                    field_meta['help_text'] = "Unicode string, may be set based on ``available_transitions`` field"
                elif field == 'immutable_state' and field_meta['help_text'] == tastypie.fields.BooleanField.help_text:
                    field_meta['help_text'] = "If ``true``, this object may not have its state modified by the user (monitoring only)"
                elif field == 'resource_uri':
                    field_meta['help_text'] = "URL for this object"
                elif field == 'available_transitions':
                    field_meta['help_text'] = "List of {'verb':"", 'state':""} for possible states (for use with POST)"
                elif field == 'available_jobs':
                    field_meta['help_text'] = "List of {'args':{}, 'class_name':"", 'confirmation':"", verb: ""} for possible " \
                                              "non-state-change jobs (for use with the ``command`` resource)"
                elif field == 'label':
                    field_meta['help_text'] = "Non-unique human readable name for presentation"

            resource_dict['list_allowed_methods'] = [m.upper() for m in resource._meta.list_allowed_methods]
            resource_dict['detail_allowed_methods'] = [m.upper() for m in resource._meta.detail_allowed_methods]
            resource_dict['ordering'] = resource._meta.ordering
            resource_dict['filtering'] = resource._meta.filtering
            for field, methods in resource_dict['filtering'].items():
                if methods == tastypie.constants.ALL_WITH_RELATIONS:
                    resource_dict['filtering'][field] = ["including dereferenced attributes"]
                if methods == tastypie.constants.ALL:
                    resource_dict['filtering'][field] = ["any filter type"]

            resource_dict['doc'] = resource.__doc__
        path = os.path.dirname(__file__)
        rst_template = open(path + "/tasty-endpoint-template.rst").read()
        template_vars = {
                    'endpoints': top_level_doc,
                    }
        django_template = Template(rst_template)
        output_rst = django_template.render(Context(template_vars))
        #open('dump.rst', 'w').write(output_rst)
        doctree = publish_doctree(output_rst)
        return doctree.children
