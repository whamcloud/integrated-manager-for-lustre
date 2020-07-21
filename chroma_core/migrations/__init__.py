# -*- coding: utf-8 -*-
from collections import namedtuple
from functools import reduce


Table = namedtuple("Table", ["name", "function_name"])


def fill_template(template):
    return lambda x: template % x._asdict()


forward_function_template = fill_template(
    """
CREATE OR REPLACE FUNCTION table_%(function_name)s_update_notify() RETURNS trigger AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        PERFORM pg_notify('table_update', '[ "' || TG_OP || '", "' || TG_TABLE_NAME || '", ' || row_to_json(NEW) || ']');
    ELSEIF TG_OP = 'UPDATE' AND OLD IS DISTINCT FROM NEW THEN
        PERFORM pg_notify('table_update', '[ "' || TG_OP || '", "' || TG_TABLE_NAME || '", ' || row_to_json(NEW) || ']');
    ELSE
        PERFORM pg_notify('table_update', '[ "' || TG_OP || '", "' || TG_TABLE_NAME || '", ' || row_to_json(OLD) || ']');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
"""
)

backward_function_template = fill_template(
    """
DROP FUNCTION IF EXISTS table_%(function_name)s_update_notify();
"""
)

forward_trigger_template = fill_template(
    """
DROP TRIGGER IF EXISTS %(name)s_notify_update
ON %(name)s;

DROP TRIGGER IF EXISTS %(name)s_notify_insert
ON %(name)s;

DROP TRIGGER IF EXISTS %(name)s_notify_delete
ON %(name)s;

CREATE TRIGGER %(name)s_notify_update
AFTER UPDATE ON %(name)s
FOR EACH ROW EXECUTE PROCEDURE table_%(function_name)s_update_notify();

CREATE TRIGGER %(name)s_notify_insert
AFTER INSERT ON %(name)s
FOR EACH ROW EXECUTE PROCEDURE table_%(function_name)s_update_notify();

CREATE TRIGGER %(name)s_notify_delete
AFTER DELETE ON %(name)s
FOR EACH ROW EXECUTE PROCEDURE table_%(function_name)s_update_notify();

"""
)

backward_trigger_template = fill_template(
    """
DROP TRIGGER IF EXISTS %(name)s_notify_update
ON %(name)s;

DROP TRIGGER IF EXISTS %(name)s_notify_insert
ON %(name)s;

DROP TRIGGER IF EXISTS %(name)s_notify_delete
ON %(name)s;
"""
)

forward_lustre_fid = """
DO $$ BEGIN
    CREATE TYPE lustre_fid AS (seq bigint, oid integer, ver integer);
EXCEPTION
    WHEN duplicate_object THEN null;
END $$;
"""

backward_lustre_fid = "DROP TYPE IF EXISTS lustre_fid;"


def compose(*args):
    def compose_inner(x):
        l = [x] + list(args)

        return reduce(lambda x, y: y(x), l)

    return compose_inner


def add_prefix(x):
    return "chroma_core_" + x


def to_table(x):
    return Table(*x)


def to_default_table(x):
    return to_table((x, "default"))


def join(xs):
    return reduce(lambda x, y: x + y, xs)


transform_tables = compose(lambda x: (add_prefix(x[0]), x[1]), to_table)

forward_function_str = forward_function_template(to_default_table("default"))

backward_function_str = backward_function_template(to_default_table("default"))

build_tables = compose(add_prefix, to_default_table)
