"""PLUMBLINE: a deliberately legacy-shaped credit union core.

Every screen is server-rendered. No control carries an id, a test id, or a label
association. Forms are table-based and their controls are identified only by the
``name`` attribute the server reads on submit.
"""

from __future__ import annotations

import os
import secrets
import time

from flask import Flask, redirect, render_template, request, session, url_for

from .data import (
    MSG_ALREADY_HELD,
    MSG_APP_ERROR,
    MSG_DIALOG,
    MSG_HOLD_POSTED,
    MSG_MAINTENANCE,
    MSG_NO_MATCH,
    MSG_NOT_AUTHORIZED,
    MSG_RESTRICTED_BANNER,
    MSG_SESSION_EXPIRED,
    MSG_SIGNON_REJECTED,
    REASONS,
    Store,
)
from .tenants import TENANTS, TenantConfig

STORE = Store()
STORE.reset()

#: One armed fault at a time. A dict so it can be cleared in place.
ARMED: dict[str, object] = {}


def faults_allowed() -> bool:
    return os.environ.get("HANDRAIL_ALLOW_FAULTS") == "1"


def create_app(tenant: str = "quarrybrook") -> Flask:
    cfg: TenantConfig = TENANTS[tenant]
    app = Flask(
        __name__,
        template_folder=os.path.join(os.path.dirname(__file__), "templates", cfg.template_dir),
    )
    app.secret_key = "plumbline-demo-secret"
    app.config["TENANT"] = cfg

    def issue_token() -> str:
        tk = secrets.token_hex(8)
        session["_tk"] = tk
        return tk

    def check_token() -> bool:
        supplied = request.form.get("_tk", "")
        return bool(supplied) and supplied == session.get("_tk")

    def current_operator():
        opid = session.get("opid")
        if not opid:
            return None
        return next((o for o in STORE.operators if o.operator_id == opid), None)

    app.jinja_env.globals["cfg"] = cfg

    FAULT_TEXT = {
        "timeout": MSG_SESSION_EXPIRED,
        "maintenance": MSG_MAINTENANCE,
        "error": MSG_APP_ERROR,
    }

    @app.before_request
    def maybe_fault():
        # The control surface is never faultable. Without this, arming a fault on a
        # broad `on_path` intercepts /__test__/* too, and a fault armed with
        # once=false can never be cleared - the endpoint that would clear it is
        # itself serving the fault page.
        if request.path.startswith("/__test__/"):
            return None
        if not faults_allowed() or not ARMED:
            return None
        on_path = str(ARMED.get("on_path", ""))
        if not request.path.startswith(on_path):
            return None
        fault = str(ARMED.get("fault", ""))
        if ARMED.get("once", True):
            ARMED.clear()
        if fault == "slow":
            time.sleep(6)
            return None
        if fault == "dialog":
            return render_template("dialog.html", text=MSG_DIALOG, back=request.path)
        return render_template("fault.html", text=FAULT_TEXT.get(fault, MSG_APP_ERROR))

    @app.post("/__test__/arm_fault")
    def arm_fault():
        if not faults_allowed():
            return "", 404
        payload = request.get_json(silent=True) or {}
        ARMED.clear()
        ARMED.update(
            {
                "fault": payload.get("fault", "error"),
                "on_path": payload.get("on_path", "/"),
                "once": payload.get("once", True),
            }
        )
        return {"armed": True}

    @app.get("/__test__/share/<share_id>")
    def share_status(share_id: str):
        """The record store, not the screen: what the verify gate asks after a replay."""
        if not faults_allowed():
            return "", 404
        share = STORE.get_share(share_id)
        if share is None:
            return {"share_id": share_id, "status": None}, 404
        return {"share_id": share.share_id, "status": share.status}

    @app.post("/__test__/reset")
    def reset():
        if not faults_allowed():
            return "", 404
        ARMED.clear()
        STORE.reset()
        return {"reset": True}

    @app.get("/")
    def root():
        return redirect(url_for("signon"))

    @app.route("/signon", methods=["GET", "POST"])
    def signon():
        if request.method == "POST":
            if not check_token():
                return "STALE FORM - RESUBMIT", 400
            operator = STORE.authenticate(request.form.get("opid", ""), request.form.get("pw", ""))
            if operator is None:
                return render_template(
                    "signon.html", token=issue_token(), error=MSG_SIGNON_REJECTED
                )
            session["opid"] = operator.operator_id
            session["branch"] = request.form.get("br", operator.branch)
            issue_token()
            return redirect(url_for("desk"))
        return render_template("signon.html", token=issue_token(), error=None)

    @app.get("/desk")
    def desk():
        if current_operator() is None:
            return redirect(url_for("signon"))
        return render_template("desk.html")

    @app.get("/menu")
    def menu():
        if current_operator() is None:
            return redirect(url_for("signon"))
        return render_template("menu.html")

    @app.route("/inquiry", methods=["GET", "POST"])
    def inquiry():
        if current_operator() is None:
            return redirect(url_for("signon"))
        results = []
        message = None
        if request.method == "POST":
            search_by = request.form.get("sby", "MBRNO")
            value = request.form.get(cfg.search_value_field, "")
            results = STORE.find_members(search_by, value)
            if not results:
                message = MSG_NO_MATCH
        return render_template("inquiry.html", results=results, message=message)

    @app.get("/member/<member_number>")
    def member(member_number: str):
        if current_operator() is None:
            return redirect(url_for("signon"))
        record = STORE.get_member(member_number)
        if record is None:
            return render_template("inquiry.html", results=[], message=MSG_NO_MATCH)
        return render_template("member.html", member=record, shares=STORE.shares_for(member_number))

    @app.get("/hold/new")
    def hold_new():
        if current_operator() is None:
            return redirect(url_for("signon"))
        share_id = request.args.get("share", "")
        return render_template("hold_new.html", share=STORE.get_share(share_id), reasons=REASONS)

    @app.post("/hold/review")
    def hold_review():
        if current_operator() is None:
            return redirect(url_for("signon"))
        return render_template(
            "hold_review.html",
            share=STORE.get_share(request.form.get("share", "")),
            reason=request.form.get("rsn", ""),
            notes=request.form.get("nt", ""),
            banner=MSG_RESTRICTED_BANNER,
        )

    @app.post("/hold/post")
    def hold_post():
        operator = current_operator()
        if operator is None:
            return redirect(url_for("signon"))
        outcome, code = STORE.place_hold(
            request.form.get("share", ""),
            request.form.get("rsn", ""),
            request.form.get("nt", ""),
            operator,
        )
        text = {
            "not_authorized": MSG_NOT_AUTHORIZED,
            "already_held": MSG_ALREADY_HELD,
            "posted": f"{MSG_HOLD_POSTED}   CONFIRMATION {code}",
        }[outcome]
        return render_template("hold_result.html", text=text, ok=outcome == "posted")

    @app.get("/signoff")
    def signoff():
        session.clear()
        return redirect(url_for("signon"))

    app.current_operator = current_operator  # type: ignore[attr-defined]
    app.issue_token = issue_token  # type: ignore[attr-defined]
    app.check_token = check_token  # type: ignore[attr-defined]
    return app
