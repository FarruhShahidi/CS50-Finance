import os

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    return apology("TODO")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":
        symb = request.form.get("symbol")

        num_shares = request.form.get("num_shares")
        if not symb:
            return apology(" Enter a  symbol", 399)
        if not lookup(symb):
            return apology("No such stock exists", 399)
        if  int(num_shares) <= 0:
            return apology("Enter  number of shares", 399)
        #check the price
        name = lookup(symb)["name"]
        price_per_share = int(lookup(symb)["price"])
        # get the cost
        buy = int(num_shares) * price_per_share
        # get the current balance
        balance = db.execute("SELECT cash FROM users WHERE id = :user_id", user_id = session["user_id"])
        if balance[0]["cash"] < buy:
            return apology("Not enough money to buy", 399)
        else:
            # enter the records to transactions database
            if db.execute("SELECT num_shares FROM transactions WHERE id=:user_id AND stock_symbol = :stock_symbol",
            user_id=session["user_id"], stock_symbol=symb):
                db.execute("UPDATE transactions SET num_shares= num_shares + :num_shares, time=datetime('now'), price=:price WHERE id=:user_id AND stock_symbol=:stock_symbol"
                , user_id=session["user_id"], stock_symbol=symb, num_shares=num_shares, price=price_per_share)
            else:
                db.execute("INSERT INTO transactions VALUES (:user_id, :name, :trans_type, :stock_symbol, :price, :num_shares, datetime('now'))"
            , user_id=session["user_id"], name=name, trans_type="buy", stock_symbol=symb, price=price_per_share, num_shares=num_shares)

            #update the balance in the users database

            db.execute("UPDATE users SET cash =cash - :buy WHERE id = :user_id", buy=buy, user_id=session["user_id"])

            return redirect("/")



    else:
         return render_template("buy.html")



@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    return apology("TODO")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            # apologize
            return apology("Enter a stock symbol", 403)
        #else, use the look up function and return
        quote = lookup(request.form.get("symbol"))

        return render_template("quoted.html", quote=quote)
    else:
        return render_template("quote.html")



@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("Please enter a username", 402)
        elif not request.form.get("password"):
            return apology("Please enter a password", 402)
        elif not request.form.get("confirm_password"):
            return apology("Please confirm your password", 402)
        # make sure the password match
        elif request.form.get("password") != request.form.get("confirm_password"):
            return apology("Passwords do not match", 402)
        hash_password = generate_password_hash(request.form.get("password"))
        # add new user to the datebase
        row = db.execute("INSERT INTO users (username, hash) VALUES (:username, :hash )",
        username = request.form.get("username"), hash = hash_password)
        if not row:
            return apology("Username already exists", 402)
        rows = db.execute("SELECT * FROM users WHERE username = :username", username = request.form.get("username"))

        #remember the user
        session["user_id"] = rows[0]["id"]

        return redirect("/")
    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""

    if request.method == "POST":
        # check if the symbol or number of shares is emty
        if not request.form.get("symbol"):
            return apology("Enter the stock symbol you want to sell", 398)
        if not request.form.get("num_shares"):
            return apology("Enter how many shares you want to sell", 398)
        #check is you have given stock and number of shares
        symb = request.form.get("symbol")
        num_shares = request.form.get("num_shares")
        get_symb = db.execute("SELECT stock_symbol FROM transactions WHERE id = :user_id", user_id = session["user_id"])
        if not get_symb:
            return apology("You do not have this stock", 398)
        total_shares = db.execute("SELECT num_shares FROM transactions WHERE stock_symbol=:stock_symbol", stock_symbol=symb)
        if total_shares[0]["num_shares"] < int(num_shares):
            return apology("You do not have enough shares to sell", 398)
        else:
            price_per_share = int(lookup(symb)["price"])
            sell = int(num_shares) * price_per_share
            # update the history table

            #update the transactions table
            db.execute("UPDATE transactions SET num_shares=num_shares-:num_shares WHERE id=:user_id AND stock_symbol=:stock_symbol"
                , user_id=session["user_id"], stock_symbol=symb, num_shares=num_shares)

            #update the users table
            db.execute("UPDATE users SET cash=cash+:sell WHERE id = :user_id", sell=sell, user_id=session["user_id"])

            return redirect("/")

    else:
        return render_template("sell.html")


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
