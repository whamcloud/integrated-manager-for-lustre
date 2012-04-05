
{% for key,endpoint in endpoints.items %}
* {{key}}_
{% endfor %}

{% for key,endpoint in endpoints.items %}

.. _{{key}}:

{{key}} ({{endpoint.list_endpoint}})
__________________________________________________________________


Description
{{endpoint.doc|safe|default:""}}

Fields
  {% for field in endpoint.schema.field_list|dictsort:"name" %}
  :``{{field.name}}``: {{field.meta.help_text|safe}} {%if field.meta.nullable%}(May be null){%endif%}
  {% endfor %}

Request options
  * Allowed list methods: {{endpoint.list_allowed_methods|join:", "|default:"none"}}
  * Allowed detail methods: {{endpoint.detail_allowed_methods|join:", "|default:"none"}}
  * Allowed ordering fields: {{endpoint.ordering|join:", "|default:"none"}}
  * Allowed filtering fields: {% if not endpoint.filtering %}none{% endif %}
  {% for field, methods in endpoint.filtering.items %}
   - {{field}} ({{methods|join:", "}}) 
  {% endfor %}

{% endfor %}


{% comment %}
{% for key,endpoint in endpoints.items %}
{{endpoint.list_endpoint}}
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

{{endpoint.doc}}

**Model Fields**:
{% for field, field_meta in endpoint.schema.fields.items %}
    ``{{field}}``:

        :Type:
            {{field_meta.type}}
        :Description: 
            {{field_meta.help_text}}
        :Nullable: 
            {{field_meta.nullable}}
        :Readonly:
            {{field_meta.readonly}} 
{% endfor %}

JSON Response ::

    {

    {% for field, field_meta in endpoint.schema.fields.items %} {{field}}:<{{field_meta.type}}>,
    {% endfor %}
    }


{% endfor %}
{% endcomment %}
