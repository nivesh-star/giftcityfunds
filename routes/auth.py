"""
routes/auth.py
Demo authentication: login, signup, logout, and the @login_required guard
used by the portfolio page and the /api/portfolio, /api/buy* endpoints.

This is a DEMO account system: passwords are properly hashed (werkzeug's
generate_password_hash/check_password_hash) so it isn't trivially insecure,
but there is no email verification, no password reset, and no real KYC --
see signup()'s docstring for what the Bank Details / Nominee steps actually
mean.

STORAGE CHANGE: these tables now live in Postgres (services/demo_db.py)
rather than a local SQLite file. SQLite can't work on Vercel -- serverless
filesystems are read-only apart from /tmp, which is wiped between
invocations, so every signup would have silently vanished.
"""

import re
from functools import wraps

from flask import Blueprint, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from services.demo_db import DemoDbError, execute, fetch_one, get_db_connection

auth_bp = Blueprint("auth", __name__)


def login_required(view_func):
    """Gate a route behind the demo session login. Redirects HTML requests
    to /login; returns 401 JSON for API requests."""
    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return {"success": False, "error": "Not logged in"}, 401
            return redirect(url_for("auth.login", next=request.path))
        return view_func(*args, **kwargs)
    return wrapped


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Demo login. This entire purchase flow is a DEMO SIMULATION: no real
    money moves, no real fund units are allotted. New accounts come from
    signup() below -- both routes write to the same demo_users table."""
    error = None
    if request.method == "POST":
        email = (request.form.get("email") or "").strip().lower()
        password = request.form.get("password") or ""
        try:
            with get_db_connection() as conn:
                user = fetch_one(
                    conn, "SELECT * FROM demo_users WHERE email = %s", (email,)
                )
        except DemoDbError as exc:
            return render_template("login.html", error=str(exc)), 503

        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["user_id"]
            session["user_email"] = user["email"]
            session["user_name"] = user["full_name"]
            next_url = request.args.get("next") or url_for("pages.portfolio")
            return redirect(next_url)
        error = "Invalid email or password."
    return render_template("login.html", error=error)


@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    """Creates a new demo account (demo_users row) and signs the person
    straight in. DEMO ONLY -- this just gates the simulated portfolio /
    Buy flow; no real KYC, no real money, no real fund units. The Bank
    Details / Nominee steps mirror what a real AMC folio application asks
    for, but nothing here is verified against any bank or registry --
    it's stored in demo_investor_profile purely so the demo account looks
    like a complete investor record."""
    error = None
    field_names = (
        "full_name", "email", "mobile_number", "bank_name", "account_number",
        "ifsc_code", "nominee_name", "nominee_relationship",
    )
    if request.method == "POST":
        form = {k: (request.form.get(k) or "").strip() for k in field_names}
        email = form["email"].lower()
        password = request.form.get("password") or ""
        confirm_password = request.form.get("confirm_password") or ""

        if not form["full_name"]:
            error = "Please enter your name."
        elif not email or "@" not in email:
            error = "Please enter a valid email address."
        elif not re.fullmatch(r"\d{10}", form["mobile_number"]):
            error = "Please enter a valid 10-digit mobile number."
        elif len(password) < 8:
            error = "Password must be at least 8 characters."
        elif password != confirm_password:
            error = "Passwords don't match."
        elif not form["bank_name"]:
            error = "Please enter your bank name."
        elif not re.fullmatch(r"\d{6,20}", form["account_number"]):
            error = "Please enter a valid bank account number."
        elif not re.fullmatch(r"[A-Za-z]{4}0[A-Za-z0-9]{6}", form["ifsc_code"]):
            error = "Please enter a valid 11-character IFSC code (e.g. HDFC0001234)."
        elif not form["nominee_name"]:
            error = "Please enter a nominee name."
        elif not form["nominee_relationship"]:
            error = "Please select the nominee's relationship to you."
        else:
            try:
                with get_db_connection() as conn:
                    existing = fetch_one(
                        conn, "SELECT user_id FROM demo_users WHERE email = %s", (email,)
                    )
                    if existing:
                        error = "An account with this email already exists."
                    else:
                        row = execute(
                            conn,
                            """INSERT INTO demo_users (email, password_hash, full_name)
                               VALUES (%s, %s, %s) RETURNING user_id""",
                            (email, generate_password_hash(password), form["full_name"]),
                        )
                        user_id = row["user_id"]
                        execute(
                            conn,
                            """INSERT INTO demo_investor_profile
                               (user_id, mobile_number, bank_name, account_number, ifsc_code,
                                nominee_name, nominee_relationship)
                               VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                            (user_id, form["mobile_number"], form["bank_name"],
                             form["account_number"], form["ifsc_code"].upper(),
                             form["nominee_name"], form["nominee_relationship"]),
                        )
            except DemoDbError as exc:
                return render_template("signup.html", error=str(exc), **form), 503

            if not error:
                session["user_id"] = user_id
                session["user_email"] = email
                session["user_name"] = form["full_name"]
                return redirect(url_for("pages.portfolio"))
    else:
        form = {k: "" for k in field_names}

    return render_template("signup.html", error=error, **form)


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("pages.index"))
