import time
import flask
from flask import Flask, request, jsonify

app = flask.Flask(__name__)

# single threaded server only
counter = {}


@app.route("/echo")
def echo():
    return flask.request.data


@app.route("/timeout")
def timeout():
    time.sleep(flask.request.args.get("sleep", 1))
    return "ok"


@app.route("/fail")
def fail():
    raise RuntimeError("failed")


@app.route("/fail5")
def fail5():
    # method, that succeeds once in a 5 subsequent calls
    if not ("fail5" in counter):
        counter["fail5"] = 0
    counter["fail5"] = counter["fail5"] + 1
    if counter["fail5"] % 5 != 0:
        raise RuntimeError("failed")
    else:
        # print(flask.request)
        content = {**request.json, "counter": counter["fail5"]}
        # content['counter'] = counter['fail5']
        return jsonify(content)


if __name__ == "__main__":
    app.run(port=5000)
