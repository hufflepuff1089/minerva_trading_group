# -*- coding: utf-8 -*-

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

app = Flask(__name__)

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

db = SQLAlchemy(app)
Session(app)


class User(db.Model):
    __tablename__ = 'user'

    id       = db.Column(db.Integer,                 primary_key = True, autoincrement = True)
    username = db.Column(db.String(32),              nullable = False, unique = True)
    email    = db.Column(db.Text(),                  nullable = False, unique = True)
    salt     = db.Column(db.String(SALT_LENGTH * 2), nullable = False) #additional security check
    password = db.Column(db.String(64),              nullable = False)
    apikey   = db.Column(db.String(256),             nullable = False, unique = True)
    capital  = db.Column(db.Integer,                 nullable = False)

    #capital va settato dinamicamente attraverso ultima entry di curr_cap in storico
    #status lo metti nel python di portfolio attraverso capital

    def __str__(self):
        return 'name: %s\nstatus: %s \ncurrent capital: %d' % (self.username, self.status, self.capital)


class Storico(db.Model):
    __tablename__ = "storico"

    id       = db.Column(db.Integer,                 primary_key = True, autoincrement = True)
    user_id  = db.Column(db.Integer,                 ForeignKey('user.id'))
    date     = db.Column(db.DateTime,                default = datetime.datetime.now, nullable = False)
    product  = db.Column(db.String(256),             nullable = False)
    price    = db.Column(db.Integer,                 nullable = False) #+ se vendi, - se compri
    curr_cap = db.Column(db.Integer,                 nullable = False)

    user     = db.relationship('User', foreign_keys = [user_id])
    #product è foreign key da mercato se lo vogliamo fare



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
        if user.apikey.startswith(APIKEY_INVALID_PREFIX):
            return redirect('/newpw')
        return func(*args, **kwargs)
    return wrapper

#SITE ROUTES: connetto le sottopagine

@app.route('/', methods = ['GET'])
def index(): #se login va a buon fine vado in portfolio, altrimenti ritorno a home
    if 'apikey' in session and User.query.filter_by(apikey = session['apikey']).first() != None:
        return redirect('/portfolio')
    return render_template('index.html')


@app.route('/about_us', methods = ['GET']) #pubblica, non richiede autentificazione
def about_us():
    return render_template('about_us.html')


@app.route('/portfolio', methods = ['GET'])
@require_auth
def portfolio():
    user = User.query.filter_by(apikey = session['apikey']).first()
    return render_template('portfolio.html', user = user)


@app.route('/sign_up', methods = ['GET', 'POST'])
def sign_up():

    if request.method == 'GET':
        if 'apikey' in session and User.query.filter_by(apikey = session['apikey']).first() != None:
            return redirect('/portfolio')
        else:
            return render_template('sign_up.html')

    elif request.method == 'POST':
        
        username = request.form['username']
        password = request.form['password']
        email    = request.form['email']
        capital  = request.form['capital']

        if len(password) < MIN_PSW_LENGTH:
            flash('Password too short, should be at least %d characters' % MIN_PSW_LENGTH, 'danger')
            return render_template('sign_up.html')

        match = USERNAME_REGEX.match(username)
        if match == None or match.start() != 0 or match.end() != len(username):
            flash(USERNAME_INVALID, 'danger')
            return render_template('sign_up.html')

        if User.query.filter_by(username=username).count() > 0:
            flash(USERNAME_TAKEN, 'danger')
            return render_template('sign_up.html')

        if User.query.filter_by(email=email).count() > 0:
            flash(USER_MAIL_TAKEN, 'danger')
            return render_template('sign_up.html')

        apikey   = os.urandom(32).hex()
        salt     = os.urandom(SALT_LENGTH)
        secret   = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 10000).hex()

        user = User(username = username,
                    email    = email,
                    salt     = salt.hex(),
                    password = secret,
                    apikey   = apikey,
                    capital  = 0)
        db.session.add(user)
        db.session.commit()
        return redirect('/login')




@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET': 
        if 'apikey' in session and User.query.filter_by(apikey = session['apikey']).first() != None:
            return redirect('/')
        else:
            return render_template('login.html')
    elif request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        match = USERNAME_REGEX.match(username)
        if match == None or match.start() != 0 or match.end() != len(username):
            flash(USERNAME_INVALID, 'danger')
            return render_template('login.html')

        users = User.query.filter_by(username = username)
        if users.count() > 1:  # shouldn't be possible due to integrity contraints
            # WTF
            return redirect('/')

        
        user = users.first()

        if user == None:
            flash(USERNAME_PASSWORD_INVALID, 'danger')
            return render_template('login.html')
            
        salt = bytes.fromhex(user.salt)
        psw  = user.password

        input_psw = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 10000).hex()

        if input_psw != psw:
            flash(USERNAME_PASSWORD_INVALID, 'danger')
            return render_template('login.html')
        
        session['apikey'] = user.apikey

        return redirect('/challenges')



@app.route('/logout', methods = ['GET'])
@require_auth
def logout():
    if 'apikey' in session:
        del session['apikey'] 
    return redirect('/')


#semmai copia init per creare base mercato, line 797
if __name__ == '__main__':
    app.run('0.0.0.0', 5005, debug=True)