from flask import Flask, abort, request

app = Flask(__name__)


@app.route("/")
def summary():
    g = app.gardener
    return {
        "pumps": g.pumps,
        "sensor_groups": g.sensor_groups,
        "last_poll": g.last_poll,
        "queued_ops": g.queue.qsize(),
    }


@app.route("/water/<pump>", methods=["POST"])
def water(pump):
    force = request.args.get("force")
    duration = request.args.get("duration")
    if duration:
        duration = int(duration)
    p = [p for p in app.gardener.pumps if p.name == pump]
    if not p:
        abort(404)
    return {"status": app.gardener.water(p[0], duration=duration, force=force)}
