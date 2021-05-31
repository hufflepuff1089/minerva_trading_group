from functools import wraps
from flask import request, session, Response, render_template, redirect, send_from_directory, abort, flash
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import and_, ForeignKey, func, desc
from sqlalchemy.types import ARRAY
from sqlalchemy import update
from flask_session import Session
from Crypto.Util.number import bytes_to_long, long_to_bytes
import hashlib
import os
import datetime
from datetime import timedelta
import hashlib
from random import randrange
import random
import re
import json
import zlib
import base64
import sys
import zipfile

SALT_LENGTH = 8
db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'user'

    id       = db.Column(db.Integer,                 primary_key = True, autoincrement = True)
    username = db.Column(db.String(32),              nullable = False, unique = True)
    email    = db.Column(db.Text(),                  nullable = False, unique = True)
    salt     = db.Column(db.String(SALT_LENGTH * 2), nullable = False) #additional security check
    password = db.Column(db.String(64),              nullable = False)
    apikey   = db.Column(db.String(256),             nullable = False, unique = True)
    capital  = db.Column(db.Integer,                 nullable = False)


    def __str__(self):
        return 'name: %s\nstatus: %s \ncurrent capital: %d' % (self.username, self.status, self.capital)


class Storico(db.Model):
    __tablename__ = "storico"

    id       = db.Column(db.Integer,                 primary_key = True, autoincrement = True)
    user_id  = db.Column(db.Integer,                 ForeignKey('user.id'))
    date     = db.Column(db.DateTime(),              default = datetime.datetime.now, nullable = False)
    amount   = db.Column(db.Integer,                 nullable = False)
    product  = db.Column(db.String(256),             ForeignKey('moneta.name'),nullable = False)
    price    = db.Column(db.Float,                   nullable = False) #+ se vendi, - se compri
    is_buy   = db.Column(db.Integer,                 nullable = False) #0 se vendi, 1 se compri

    user     = db.relationship('User', foreign_keys = [user_id])
    moneta   = db.relationship('Moneta', foreign_keys = [product])

class Moneta(db.Model):
    __tablename__ = "moneta"

    name       = db.Column(db.String(256),             primary_key = True)
    value      = db.Column(db.Float,                   nullable = False)

monete=['algorand','bitcoin','chainlink','dai','ethereum','sapienzacoin','paxos','revain','solve','sora','stellar','symbol','tether','tezos','waves']

def wallet_to_csv(path, id_intended):
    owned_monete={}
    for i in monete:
        owned_monete[i]=0
        for owned_moneta in db.session.query(func.sum(Storico.amount)).filter_by(user_id=int(id_intended), is_buy=1, product=i):
            if owned_moneta[0]==None:
                pass
            else:
                owned_monete[i]+=owned_moneta[0]
        for owned_moneta in db.session.query(func.sum(Storico.amount)).filter_by(user_id=int(id_intended), is_buy=0, product=i):
            if owned_moneta[0]==None:
                pass
            else:
                owned_monete[i]-=owned_moneta[0]
    output="PRODUCT,AMOUNT\n"
    cap = ""
    for x in db.session.query(User.capital).filter_by(id=id_intended):
        cap = str(x[0])
    output += "CAPITAL," + cap +"\n"

    for owned in owned_monete:
        output+=owned+","+str(owned_monete[owned])+"\n"
    open(path,"w").write(output)

def transactions_to_csv(path, id_intended):
    transactions = Storico.query.order_by(Storico.date.desc()).all()
    output="ID,USER_ID,DATE,AMOUNT,PRODUCT,PRICE,IS_BUY\n"
    for transaction in transactions:
        if str(transaction.user_id)==str(id_intended):
            output+=str(transaction.id)+","+str(transaction.user_id)+","+str(transaction.date)+","+str(transaction.amount)+","+str(transaction.product)+","+str(transaction.price)+","+str(transaction.is_buy)+"\n"
    open(path,"w").write(output)

def users_to_csv(path, user_intended):
    users = User.query.all()
    output="ID,USERNAME,EMAIL,SALT,PASSWORD,APIKEY,CAPITAL\n"
    for user in users:
        if user.username.lower()==user_intended.lower():
            output+=str(user.id)+","+user.username+","+str(user.email)+","+user.salt+","+user.password+","+user.apikey+","+str(user.capital)+"\n"
    open(path,"w").write(output)

def buy_fun(user, prod_from, prod_to, prod_price, amount_from):
    prod_from = prod_from.lower()
    prod_to = prod_to.lower()
    if prod_from not in monete or prod_to not in monete:
        flash("Sorry, crypto not in stock - order: aborted.", 'danger')
        print("\n   >>> MINERVA SERVER TRACE: error, crypto not in stock - order aborted.\n")
    else:
        amount_from = float(amount_from)
        prod_price = float(prod_price)
        amount_to,price_to=0,0
        for value_to in db.session.query(Moneta.value).filter_by(name=prod_to):
            amount_to=float(prod_price/value_to[0])
            price_to=value_to[0]
        actual_amount_from=0
        for owned_moneta in db.session.query(func.sum(Storico.amount)).filter_by(user_id=user.id, is_buy=1, product=prod_from):
            if owned_moneta[0]!=None:
                actual_amount_from+=owned_moneta[0]
        for owned_moneta in db.session.query(func.sum(Storico.amount)).filter_by(user_id=user.id, is_buy=0, product=prod_from):
            if owned_moneta[0]!=None:
                actual_amount_from-=owned_moneta[0]
        if user.capital<prod_price*amount_from: # or actual_amount_from<amount_from:
            flash("Sorry, not enough money in capital to place the order - order: aborted.", 'danger')
            print("\n   >>> MINERVA SERVER TRACE: error, negative capital - order aborted.\n")
        else:
            user.capital-=prod_price*amount_from

            print("BUY: ", prod_price, price_to)
            storico=Storico(user_id=user.id,date=datetime.datetime.strptime(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S"),amount=amount_from,product=prod_to,price=price_to,is_buy=1)
            db.session.add(storico)
            storico=Storico(user_id=user.id,date=datetime.datetime.strptime(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S"),amount=amount_from,product=prod_from,price=-prod_price,is_buy=0)
            db.session.add(storico)
            db.session.commit()
            wallet_to_csv('static/me.csv', user.id)    
            transactions_to_csv("static/transactions_me.csv", user.id)

def sell_fun(user, prod_to, prod_from, prod_price, amount_from):
    prod_from = prod_from.lower()
    prod_to = prod_to.lower()
    if prod_from not in monete or prod_to not in monete:
        flash("Sorry, crypto not in stock - order: aborted.", 'danger')
        print("\n   >>> MINERVA SERVER TRACE: error, crypto not in stock - order aborted.\n")
    else:
        amount_from = float(amount_from)
        prod_price = float(prod_price)
        amount_to,price_to=0,0
        for value_to in db.session.query(Moneta.value).filter_by(name=prod_to):
            amount_to=float(prod_price/value_to[0])
            price_to=value_to[0]
        actual_amount_from=0
        for owned_moneta in db.session.query(func.sum(Storico.amount)).filter_by(user_id=user.id, is_buy=1, product=prod_from):
            if owned_moneta[0]!=None:
                actual_amount_from+=owned_moneta[0]
        for owned_moneta in db.session.query(func.sum(Storico.amount)).filter_by(user_id=user.id, is_buy=0, product=prod_from):
            if owned_moneta[0]!=None:
                actual_amount_from-=owned_moneta[0]
        if user.capital<prod_price*amount_from: # or actual_amount_from < amount_from:
            flash("Sorry, not enough money in capital to place the order - order: aborted.", 'danger')
            print("\n   >>> MINERVA SERVER TRACE: error, negative capital - order aborted.\n")
        else:
            user.capital+=prod_price*amount_from
            print("SELL: ", prod_price, price_to)
            storico=Storico(user_id=user.id,date=datetime.datetime.strptime(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S"),amount=amount_from,product=prod_to,price=-price_to,is_buy=1)
            db.session.add(storico)
            storico=Storico(user_id=user.id,date=datetime.datetime.strptime(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "%Y-%m-%d %H:%M:%S"),amount=amount_from,product=prod_from,price=prod_price,is_buy=0)
            db.session.add(storico)
            db.session.commit()
            wallet_to_csv('static/me.csv', user.id)    
            transactions_to_csv("static/transactions_me.csv", user.id)

def random_date(start, end):
    delta = end - start
    int_delta = (delta.days * 24 * 60 * 60) + delta.seconds
    random_second = randrange(int_delta)
    return start + timedelta(seconds=random_second)

def populate_me(id_intended):
    for i in range(100):
        p = round(random.uniform(-2.0,2.0), 2)
        storico=Storico(user_id=id_intended,date=random_date(datetime.datetime.strptime('25/5/2020 0:00 AM', '%d/%m/%Y %H:%M %p'), datetime.datetime.strptime('25/5/2021 0:00 AM', '%d/%m/%Y %H:%M %p')),amount=random.randint(0,10),product=random.choice(monete),price= p,is_buy= 1 if p <= 0 else 0 ) #random.randint(0,1)
        db.session.add(storico)
    db.session.commit()
    print("\n   >>> MINERVA SERVER TRACE: DB - populating Storico\n")

def populate_moneta():
    for i in monete:
        moneta=Moneta(name=i, value=round(random.uniform(0.1,3.0), 2))
        db.session.add(moneta)
    db.session.commit()
    print("\n   >>> MINERVA SERVER TRACE: DB - populating Moneta\n")

    