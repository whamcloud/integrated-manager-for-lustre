#
# ========================================================
# Copyright (c) 2012 Whamcloud, Inc.  All rights reserved.
# ========================================================


class ApiResource(object):
    def __init__(self, *args, **kwargs):
        self.__attributes = kwargs
        self.list_columns = ["id"]

    def __getattr__(self, key):
        return self.__attributes[key]

    def __getitem__(self, key):
        return self.__attributes[key]

    @property
    def all_attributes(self):
        return self.__attributes

    def as_header(self):
        return self.list_columns

    def as_row(self):
        row = []
        for key in self.list_columns:
            try:
                val = getattr(self, key)
                # Don't just try: this because catching TypeErrors can
                # mask problems inside the callable.
                if callable(val):
                    row.append(val())
                else:
                    row.append(val)
            except KeyError:
                row.append("")

        return row

    def __str__(self):
        return " | ".join([str(f) for f in self.as_row()])

    # http://stackoverflow.com/a/1094933/204920
    def fmt_bytes(self, bytes):
        import math
        if bytes is None or math.isnan(float(bytes)):
            return "NaN"
        bytes = float(bytes)
        for x in ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "YiB", "ZiB"]:
            if bytes < 1024.0:
                return "%3.1f%s" % (bytes, x)
            bytes /= 1024.0
        # fallthrough, bigger than ZiB?!?!
        return "%d" % bytes

    def fmt_num(self, num):
        import math
        if num is None or math.isnan(float(num)):
            return "NaN"
        num = float(num)
        for x in ["", "K", "M", "G", "P", "E", "Y", "Z"]:
            if num < 1000.0:
                return "%3.1f%s" % (num, x)
            num /= 1000.0
        # fallthrough
        return "%d" % num

    def pretty_time(self, in_time):
        from datetime import datetime as dt
        from dateutil.tz import tzlocal, tzutc
        local_tz = tzlocal()
        local_midnight = dt.now(local_tz).replace(hour=0, minute=0,
                                                  second=0, microsecond=0)
        in_time = in_time.replace(tzinfo=tzutc())
        out_time = in_time.astimezone(local_tz)
        if out_time < local_midnight:
            return out_time.strftime("%Y/%m/%d %H:%M:%S")
        else:
            return out_time.strftime("%H:%M:%S")


class Host(ApiResource):
    def __init__(self, *args, **kwargs):
        super(Host, self).__init__(*args, **kwargs)
        # FIXME: Figure out bad interaction between role as a resource
        # field and as a filter.
        #self.list_columns.extend(["fqdn", "role", "state", "nids", "last_contact"])
        self.list_columns.extend(["fqdn", "state", "nids", "last_contact"])

    def last_contact(self):
        from dateutil.parser import parse
        last_contact = self.all_attributes['last_contact']
        if last_contact is not None:
            return self.pretty_time(parse(last_contact))
        else:
            return "Never"


class Target(ApiResource):
    def __init__(self, *args, **kwargs):
        super(Target, self).__init__(*args, **kwargs)
        self.list_columns.extend(["name", "state", "primary_path"])

    def primary_path(self):
        try:
            primary_node = [vn for vn in self.volume['volume_nodes']
                                        if vn['primary']][0]
            return "%s:%s" % (primary_node['host_label'], primary_node['path'])
        except IndexError:
            return "Unknown"


class Filesystem(ApiResource):
    def __init__(self, *args, **kwargs):
        super(Filesystem, self).__init__(*args, **kwargs)
        self.list_columns.extend(["name", "state", "clients", "files", "space"])

    def files(self):
        # Freaking Nones
        files_total = float("nan") if self.files_total is None else self.files_total
        files_free = float("nan") if self.files_free is None else self.files_free
        return "%s/%s" % (self.fmt_num(files_free), self.fmt_num(files_total))

    def space(self):
        bytes_total = float("nan") if self.bytes_total is None else self.bytes_total
        bytes_free = float("nan") if self.bytes_free is None else self.bytes_free
        return "%s/%s" % (self.fmt_bytes(bytes_free), self.fmt_bytes(bytes_total))

    def clients(self):
        return "%d" % self.client_count


class Volume(ApiResource):
    def __init__(self, *args, **kwargs):
        super(Volume, self).__init__(*args, **kwargs)
        self.list_columns.extend(["label", "size", "status", "servers"])

    def size(self):
        return self.fmt_bytes(self.all_attributes['size'])

    def servers(self):
        nodes = []
        for node in self.volume_nodes:
            if node['primary']:
                nodes.insert(0, node['host_label'])
            else:
                nodes.append(node['host_label'])
        return ",".join(nodes)
