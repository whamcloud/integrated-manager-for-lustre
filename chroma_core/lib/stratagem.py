import requests
import settings
import json

from toolz.functoolz import pipe, partial

temp_stratagem_measurement = "temp_stratagem_scan"

size_distribution_name_table = {
    "size < 1m": "less_than_1m",
    "1m <= size < 1g": "greater_than_equal_1m_less_than_1g",
    "size >= 1g": "greater_than_equal_1g",
    "size >= 1t": "greater_than_equal_1t",
}

labels = {
    "less_than_1m": "<\\\ 1\\\ Mib",
    "greater_than_equal_1m_less_than_1g": ">\\\=\\\ 1\\\ Mib\\\,\\\ <\\\ 1\\\ GiB",
    "greater_than_equal_1g": ">\\\=\\\ 1\\\ GiB",
    "greater_than_equal_1t": ">\\\=\\\ 1\\\ TiB",
}

filter_out_other_counter = partial(filter, lambda counter: counter.get("name").lower() != "other")


def flatten(xs):
    return [item for l in xs for item in l]


def tuple_to_equals(xs):
    return "{}={}".format(*xs)


def create_stratagem_influx_point(measurement, tags, fields):
    return "{},{} {} {}".format(
        measurement, ",".join(map(tuple_to_equals, tags)), ",".join(map(tuple_to_equals, fields)), ""
    ).rstrip()


def parse_size_distribution(measurement, fs_name, labels, counters):
    return pipe(
        counters,
        filter_out_other_counter,
        partial(map, lambda x: x.update({"name": size_distribution_name_table[x.get("name").lower()]}) or x),
        partial(
            map,
            lambda x: create_stratagem_influx_point(
                measurement,
                [
                    ("group_name", "size_distribution"),
                    ("counter_name", x.get("name")),
                    ("label", labels.get(x.get("name"))),
                    ("fs_name", fs_name),
                ],
                [("count", x.get("count")), ("size", x.get("size"))],
            ),
        ),
    )


def parse_user_distribution(measurement, fs_name, counters):
    return pipe(
        counters,
        partial(filter, lambda x: "classify" in x),
        partial(map, lambda x: x.get("classify")),
        partial(map, lambda x: map(lambda y, x=x: y.update({"attr_type": x.get("attr_type")}) or y, x.get("counters"))),
        partial(flatten),
        partial(
            map,
            lambda x: create_stratagem_influx_point(
                measurement,
                [
                    ("group_name", "user_distribution"),
                    ("classify_attr_type", x.get("attr_type")),
                    ("counter_name", x.get("name")),
                    ("fs_name", fs_name),
                ],
                [("count", x.get("count")), ("size", x.get("size"))],
            ),
        ),
    )


def parse_stratagem_results_to_influx(measurement, fs_name, stratagem_results_json):
    parse_fns = {
        "size_distribution": partial(parse_size_distribution, measurement, fs_name, labels),
        "user_distribution": partial(parse_user_distribution, measurement, fs_name),
    }

    group_counters = stratagem_results_json.get("group_counters")

    return pipe(
        [],
        partial(reduce, lambda out, cur: out + [(cur.get("name"), cur.get("counters"))], group_counters),
        partial(filter, lambda xs: xs[0] not in ["warn_fids", "purge_fids", "filesync", "cloudsync"]),
        partial(map, lambda xs, parse_fns=parse_fns: parse_fns[xs[0]](xs[1])),
        partial(flatten),
    )


def clear_scan_results(clear_measurement_query):
    response = requests.post(
        "{}/query".format(settings.INFLUXDB_PROXY_PASS),
        params={"db": settings.INFLUXDB_STRATAGEM_SCAN_DB, "q": clear_measurement_query},
    )

    response.raise_for_status()


def record_stratagem_point(point):
    response = requests.post(
        "{}/write?db={}".format(settings.INFLUXDB_PROXY_PASS, settings.INFLUXDB_STRATAGEM_SCAN_DB), data=point
    )

    response.raise_for_status()


def aggregate_points(measurement_query):
    response = requests.get(
        "{}/query".format(settings.INFLUXDB_PROXY_PASS),
        params={"db": settings.INFLUXDB_STRATAGEM_SCAN_DB, "epoch": 0, "q": measurement_query},
    )

    results = json.loads(response._content).get("results")[0]
    series = results.get("series")
    if not series:
        return []

    values = series[0].get("values")
    columns = series[0].get("columns")

    points = [dict(zip(columns, xs)) for xs in values]

    counter_names = set((point.get("counter_name") for point in points))

    grouped_points = reduce(
        lambda agg, cname: agg + [[x for x in points if x.get("counter_name") == cname]], counter_names, []
    )

    for xs in grouped_points:
        xs.sort(key=lambda k: k["time"], reverse=True)

    def reduce_points(xs):
        return reduce(lambda x, y: dict(x, **{"count": x["count"] + y["count"], "size": x["size"] + y["size"]}), xs)

    return [reduce_points(xs) for xs in grouped_points]


def join_entries_with_new_line(entries):
    return "\n".join(entries)


def submit_aggregated_data(measurement, fs_name, aggregated):
    points = [
        (
            [
                ("classify_attr_type", point.get("classify_attr_type")),
                ("group_name", point.get("group_name")),
                ("label", point.get("label")),
                ("counter_name", point.get("counter_name")),
                ("fs_name", fs_name),
            ],
            [("count", point.get("count")), ("size", point.get("size"))],
        )
        for point in aggregated
    ]

    point = join_entries_with_new_line([create_stratagem_influx_point(measurement, xs[0], xs[1]) for xs in points])

    return record_stratagem_point(point)
