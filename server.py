from functools import wraps
from flask import request, session, Response, render_template, redirect, send_from_directory, abort, flash
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, ForeignKey, func
from sqlalchemy.types import ARRAY
from flask_session import Session
from Crypto.Util.number import bytes_to_long, long_to_bytes
import hashlib
import os
import datetime
from datetime import timedelta
import hashlib
import random
import re
import json
import zlib
import base64
import sys
import zipfile
from database import *
import csv

app = Flask(__name__)
db.app = app
db.init_app(app)

#flag login
USERNAME_REGEX = re.compile(r'[0-9a-zA-Z_!@#€\-&+]{4,32}')
USERNAME_INVALID = 'Invalid username, must match [0-9a-zA-Z_!@#€-&+]{4,32}'
USERNAME_PASSWORD_INVALID = 'Wrong username and/or password'
USERNAME_TAKEN = 'Username already taken'
USER_MAIL_TAKEN = 'Email already registered'

MIN_PSW_LENGTH = 6
APIKEY_INVALID_PREFIX = "invalid_"

app.secret_key = 'TSMBhyuIY8l0BYlYAQoA1dUYEGJzmTJADZaPWCJ4ucbAwwnePQ3t/dsLdz/ghfWL'

SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
SALT_LENGTH = 8


#flask & SQLalchemy configs
app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_USE_SIGNER'] = True #cookie cifrati con secret key
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)
app.config['SESSION_FILE_THRESHOLD'] = 500

app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_POOL_RECYCLE'] = 299
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

app.config['TEMPLATES_AUTO_RELOAD'] = True


Session(app)


#authentification decorator
def require_auth(func):
    '''Checks whether user is logged in or redirect to login.'''
    @wraps(func)
    def wrapper(*args, **kwargs):
        if 'apikey' not in session:
            return redirect('/')
        user = User.query.filter_by(apikey = session['apikey']).first()
        if user == None:
            return redirect('/')
        return func(*args, **kwargs)
    return wrapper

#SITE ROUTES: connetto le sottopagine

@app.route('/', methods = ['GET'])
def index(): #se login va a buon fine vado in portfolio, altrimenti ritorno a home
    print("\n   >>> MINERVA SERVER TRACE: @index\n")
    if 'apikey' in session and User.query.filter_by(apikey = session['apikey']).first() != None:
        return redirect('/portfolio')
    return render_template('index.html')


@app.route('/about_us', methods = ['GET']) #pubblica, non richiede autentificazione
def about_us():
    print("\n   >>> MINERVA SERVER TRACE: @about_us\n")
    return render_template('about_us.html')


@app.route('/portfolio', methods = ['GET', 'POST'])
@require_auth
def portfolio():
    if request.method == 'POST':
        print("\n   >>> MINERVA SERVER TRACE: placing order\n")
        user = User.query.filter_by(apikey = session['apikey']).first()
        if(request.form['tipo'] == "sell"):
            coin_from = request.form['from_crypto']
            coin_to = request.form['to_crypto']
            price    = request.form['price']
            amount  = request.form['amount']
            sell_fun(user, coin_from, coin_to, price, amount)

        else:
            if(request.form['tipo'] == "buy"):
                coin_from = request.form['from_crypto']
                coin_to = request.form['to_crypto']
                price    = request.form['price']
                amount  = request.form['amount']
                buy_fun(user, coin_from, coin_to, price, amount)

        return redirect("/portfolio")

    if request.method == 'GET':
        print("\n   >>> MINERVA SERVER TRACE: @portfolio\n")
        user = User.query.filter_by(apikey = session['apikey']).first()

        wallet_to_csv('static/me.csv', user.id)    
        transactions_to_csv("static/transactions_me.csv", user.id)
        return render_template('portfolio.html', user = user)


@app.route('/sign_up', methods = ['POST'])
def sign_up():

    if request.method == 'POST':
        
        username = request.form['username']
        password = request.form['password']
        email    = request.form['email']
        capital  = request.form['capital']

        print("\n   >>> MINERVA SERVER TRACE: @signup, form ok\n")

        if len(password) < MIN_PSW_LENGTH:
            flash('Password too short, should be at least %d characters' % MIN_PSW_LENGTH, 'danger')
            print("\n   >>> MINERVA SERVER TRACE: error, password too short (min 6 chars)\n")
            return redirect('/')

        match = USERNAME_REGEX.match(username)
        if match == None or match.start() != 0 or match.end() != len(username):
            flash(USERNAME_INVALID, 'danger')
            print("\n   >>> MINERVA SERVER TRACE: error, username invalid\n")
            return redirect('/')

        if User.query.filter_by(username=username).count() > 0:
            flash(USERNAME_TAKEN, 'danger')
            print("\n   >>> MINERVA SERVER TRACE: error, username taken\n")
            return redirect('/')

        if User.query.filter_by(email=email).count() > 0:
            flash(USER_MAIL_TAKEN, 'danger')
            print("\n   >>> MINERVA SERVER TRACE: error, email taken\n")
            return redirect('/')

        apikey   = os.urandom(32).hex()
        salt     = os.urandom(SALT_LENGTH)
        secret   = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 10000).hex()

        user = User(username = username,
                    email    = email,
                    salt     = salt.hex(),
                    password = secret,
                    apikey   = apikey,
                    capital  = capital)
        db.session.add(user)
        db.session.commit()

        users = User.query.filter_by(username = username)
        user = users.first()
        session['apikey'] = user.apikey
        populate_me(user.id)
        db.session.commit()
        print("\n   >>> MINERVA SERVER TRACE: redirecting to PORTFOLIO\n")
        return redirect('/portfolio')




@app.route('/login', methods=['POST', 'GET'])
def login():
    print("\n   >>> MINERVA SERVER TRACE: @login\n")
    if request.method == 'GET': 
        if 'apikey' in session and User.query.filter_by(apikey = session['apikey']).first() != None:
            flash("wrong apikey", 'danger')
            print("\n   >>> MINERVA SERVER TRACE: wrong apikey, redirecting to HOME\n")
            return redirect('/')
        else:
            print("\n   >>> MINERVA SERVER TRACE: redirecting to PORTFOLIO - solving issues with passing parameters\n")
            return redirect('/portfolio')

    elif request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        match = USERNAME_REGEX.match(username)
        if match == None or match.start() != 0 or match.end() != len(username):
            flash(USERNAME_INVALID, 'danger')
            print("\n   >>> MINERVA SERVER TRACE: error no such user in db, redirecting to HOME\n")
            return redirect('/')

        users = User.query.filter_by(username = username)
        if users.count() > 1:  # shouldn't be possible due to integrity contraints
            # WTF
            flash("double user", 'danger')
            print("\n   >>> MINERVA SERVER TRACE: error double user, redirecting to HOME\n")
            return redirect('/')

        
        user = users.first()

        if user == None:
            flash(USERNAME_PASSWORD_INVALID, 'danger')
            print("\n   >>> MINERVA SERVER TRACE: error no user, redirecting to HOME\n")
            return redirect('/')
            
        salt = bytes.fromhex(user.salt)
        psw  = user.password

        input_psw = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 10000).hex()

        if input_psw != psw:
            print("\n   >>> MINERVA SERVER TRACE: error invalid password, redirecting to HOME\n")
            flash(USERNAME_PASSWORD_INVALID, 'danger')
            return redirect('/')
        
        session['apikey'] = user.apikey

        print("\n   >>> MINERVA SERVER TRACE: redirecting to PORTFOLIO\n")
        return redirect('/portfolio')



@app.route('/logout', methods = ['GET'])
@require_auth
def logout():
    if 'apikey' in session:
        del session['apikey'] 
    print("\n   >>> MINERVA SERVER TRACE: leaving page, redirecting to HOME\n")
    return redirect('/')


if __name__ == '__main__':
    
    db.drop_all()
    print("\n   >>> MINERVA SERVER TRACE: dropping DB\n")
    db.create_all()
    populate_moneta()
    db.session.commit()
    print("\n   >>> MINERVA SERVER TRACE: DB on and populated\n")
    print("\n   >>> MINERVA SERVER TRACE: MTG website is online!\n")
    app.run('0.0.0.0', 5005, debug=True)