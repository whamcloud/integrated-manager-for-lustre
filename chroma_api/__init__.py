# Copyright (c) 2021 DDN. All rights reserved.
# Use of this source code is governed by a MIT-style
# license that can be found in the LICENSE file.


from chroma_core.services import log_register

from chroma_api.related_field import RelatedField

assert RelatedField  # silence pyflakes

api_log = log_register("django.request.tastypie")
