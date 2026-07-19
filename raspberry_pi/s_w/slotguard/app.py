import sqlite3
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    jsonify,
    redirect,
    render_template,
    request,
    url_for,
)

from database import (
    allow_due_schedules,
    create_schedule,
    get_schedules,
    init_db,
)


app = Flask(__name__)

init_db()

VOICE_FILE = (
    Path(__file__).resolve().parent
    / "audio"
    / "medicine_time.mp3"
)


def play_voice():
    if not VOICE_FILE.is_file():
        print(f"[VOICE] 음성 파일을 찾을 수 없습니다: {VOICE_FILE}")
        return

    result = subprocess.run(
        [
            "/usr/bin/cvlc",
            "--intf", "dummy",
            "--play-and-exit",
            "--no-video",
            "-A", "alsa",
            "--alsa-audio-device", "sysdefault:CARD=Headphones",
            str(VOICE_FILE),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )

    if result.returncode != 0:
        print(f"[VOICE] 음성 재생 실패: returncode={result.returncode}")


def schedule_voice_worker():
    while True:
        current_minute = datetime.now().strftime("%Y-%m-%d %H:%M")

        try:
            allowed_count = allow_due_schedules(current_minute)

            if allowed_count > 0:
                print(
                    f"[VOICE] {current_minute}: "
                    f"복약 일정 {allowed_count}건 허용"
                )
                play_voice()

        except sqlite3.Error as error:
            print(f"[VOICE] 일정 조회 실패: {error}")

        time.sleep(1)


@app.get("/")
def dashboard():
    schedules = get_schedules()

    counts = {
        "total": len(schedules),
        "waiting": 0,
        "allowed": 0,
        "dispensed": 0,
        "missed": 0,
    }

    for schedule in schedules:
        status = schedule["status"]

        if status == "WAITING":
            counts["waiting"] += 1
        elif status == "ALLOWED":
            counts["allowed"] += 1
        elif status == "DISPENSED":
            counts["dispensed"] += 1
        elif status == "MISSED":
            counts["missed"] += 1

    return render_template(
        "dashboard.html",
        counts=counts,
    )


@app.route("/schedules", methods=["GET", "POST"])
def schedule_page():
    error = None

    if request.method == "POST":
        try:
            pack_id = int(request.form["pack_id"])
            slot = int(request.form["slot"])

            scheduled_date = request.form["scheduled_date"]
            scheduled_time = request.form["scheduled_time"]

            if pack_id < 1:
                raise ValueError

            if slot < 1 or slot > 10:
                raise ValueError

            scheduled_at = datetime.strptime(
                f"{scheduled_date} {scheduled_time}",
                "%Y-%m-%d %H:%M",
            ).strftime("%Y-%m-%d %H:%M")

            create_schedule(
                pack_id=pack_id,
                slot=slot,
                scheduled_at=scheduled_at,
            )

            return redirect(url_for("schedule_page"))

        except (KeyError, ValueError):
            error = "입력값을 확인하십시오."

        except sqlite3.IntegrityError:
            error = "같은 포장 회차에 이미 등록된 슬롯입니다."

    schedules = get_schedules()

    return render_template(
        "schedules.html",
        schedules=schedules,
        error=error,
    )


@app.get("/api/status")
def api_status():
    try:
        schedules = get_schedules()

    except sqlite3.Error:
        return jsonify({
            "web": "OK",
            "database": "ERROR",
            "uart": "NOT_CONNECTED",
        }), 500

    return jsonify({
        "web": "OK",
        "database": "OK",
        "uart": "NOT_CONNECTED",
        "schedule_count": len(schedules),
    })


if __name__ == "__main__":
    threading.Thread(
        target=schedule_voice_worker,
        daemon=True,
    ).start()

    app.run(
        host="0.0.0.0",
        port=5000,
        debug=False,
    )
