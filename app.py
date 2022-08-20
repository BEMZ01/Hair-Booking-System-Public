# -*- coding: utf-8 -*-
###############################
#                             #
#       Hair Booking App      #
#       © BEMZlabs            #
#       2022                  #
#       For Licence see       #
#       LICENSE.md            #
#                             #
###############################

from pprint import pprint
import ast
import datetime  # required for calendar support
from dateutil.relativedelta import relativedelta  # required for google calendar
import sqlite3 as sql  # required to store and edit database and tables
import time  # time management
import uuid  # generate uuids for security in the config.yml
from flask import Flask, request, url_for, render_template, redirect, make_response, flash  # create a webserver
from flask_toastr import Toastr  # Toast Notifications within browser
import re  # Regular Expressions
import yaml  # easy read / write of yml files
from werkzeug.exceptions import HTTPException  # Error handeler for Flask
import os  # allow us to run commands through terminal, used with Oauth2.0 login
import hashlib  # encryption of data
import requests as req  # allow to get form data back from forms
import smtplib  # allow the handleing of smtp packets
from email.mime.multipart import MIMEMultipart  # edit and creation of SMTP packets
from email.mime.text import MIMEText
from googleapiclient.discovery import build  # Google API (Oauth 2.0 login / calendar)
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import traceback  # to get in depth errors
import pyqrcode

print("initilizing Flask")
app = Flask(__name__, static_url_path='/')  # create a flask instance
print("Initilize Toasr")
toastr = Toastr(app)
toastr.init_app(app)


# Cookies currently in use:
# "uID" Allows for user to be signed in. Required
# this log is needed for a cookie policy. (Because i will 100% forget what names I have used)


def render_text(text):  # replace placeholder text with actual data
    name = request.cookies.get('uID')
    business = CONFIG["business name"]
    dat = time.strftime(r"%d/%m/%Y", time.localtime())
    text = text.replace("%%NAME%%", name)
    text = text.replace("%%BUSINESS%%", business)
    text = text.replace("%%DATE%%", dat)
    return text


def google_login():  # handles google logins
    creds = None
    """The file token.json stores the user's access and refresh tokens, and is
    created automatically when the authorization flow completes for the first
    time."""
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                os.remove("token.json")
                return False
        else:
            try:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
            except FileNotFoundError:
                return False
            creds = flow.run_console(
                authorization_prompt_message='Please visit this URL to authorize Google Calendar sync: {url}',
                authorization_code_message='\n\nEnter the authorization code: ')
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('calendar', 'v3', credentials=creds)
    print("Successfully Connected to google calendar!")
    return service


def send_email(cc, header, content):  # handles email sending
    """This Subroutine will attempt to create a MIMEMultipart object to build 
    an email package containing data needed to send an email. The data will 
    then be set in the email and sent, if this is successful the program will
    return to the main program with no data, however if an error occurs the
    program will halt."""
    try:
        mail_content = content
        # The mail addresses and password
        sender_address = CONFIG["email"]["address"]
        sender_pass = CONFIG["email"]["app-password"]
        # Setup the MIME
        message = MIMEMultipart()
        message['From'] = sender_address
        message['To'] = cc
        message['Subject'] = header  # The subject line
        # The body and the attachments for the mail
        message.attach(MIMEText(mail_content, ''))
        # Create SMTP session for sending the mail
        session = smtplib.SMTP('smtp.gmail.com', 587)  # use gmail with port
        session.starttls()  # enable security
        session.login(sender_address, sender_pass)  # login with mail_id and password
        text = message.as_string()
        session.sendmail(sender_address, cc, text)
        session.quit()
        return None
    except smtplib.SMTPAuthenticationError as err:
        raise ("Login Details are incorrect! Please check config.yml for more information. (" + str(err) + ")")


def update():
    """This subroutine is called on startup and allows for the server to see if the client needs to be updated.
    Whilst this could use subprocess.run() to summon a command prompt to auto-update the program, it was
    out of scope of this program and as such the feature was not added."""
    # pull config.yml from Github repo (master)
    r = req.get("https://raw.githubusercontent.com/BEMZ01/Hair-Booking-System-Public/master/config.yml")
    if not r.ok:
        print("\n\nGithub Repo cannot be found! Did I get removed? :(")
        time.sleep(3)
        return False
    open("latest.yml", 'wb').write(r.content).close()
    latest = load_yaml("latest.yml")
    current = load_yaml("config.yml")
    os.remove("latest.yml")
    if latest["version"] > current["version"]:
        return True
    else:
        return False


def generate_database():
    """Really simple subroutine to check if the database file exists
    if not the program will generate a new database and automatically
    add tables into the database""" 
    print("Checking Database integrity")
    if os.path.exists('storage.db'):
        print("Database Already Exists")
        return True
    else:
        print("Database not found!")
        sql_create_accounts_table = """CREATE TABLE IF NOT EXISTS accounts (
                                        id INTEGER PRIMARY KEY,
                                        user text NOT NULL UNIQUE,
                                        pass text NOT NULL,
                                        email text NOT NULL UNIQUE,
                                        active integer NOT NULL,
                                        uuid text NOT NULL UNIQUE,
                                        UNIQUE(user,id, email)
                                    ) """
        sql_create_dates_table = """CREATE TABLE IF NOT EXISTS dates (
                                        id INTEGER PRIMARY KEY,
                                        user text NOT NULL,
                                        date_start INTEGER NOT NULL,
                                        length INTEGER NOT NULL,
                                        price FLOAT NOT NULL,
                                        desc text NOT NULL,
                                        products text NOT NULL
     ) """
        with sql.connect('storage.db') as db:
            cursor = db.cursor()
            cursor.execute(sql_create_accounts_table)
            cursor.execute(sql_create_dates_table)
            db.commit()
            cursor.close()
        return True


def wipe_dates():  # remove dates within database
    try:
        sql_create_dates_table = """CREATE TABLE IF NOT EXISTS dates (
    id INTEGER PRIMARY KEY,
    user text NOT NULL,
    date_start INTEGER NOT NULL,
    length INTEGER NOT NULL,
    price FLOAT NOT NULL,
    products text NOT NULL,
    desc text NOT NULL
 ) """
        with sql.connect('storage.db') as db:
            cursor = db.cursor()
            cursor.execute("DROP TABLE dates")
            cursor.execute(sql_create_dates_table)
            db.commit()
            cursor.close()
    except Exception:
        pass


def verify_file(file_name):  # check if file exists
    try:
        with open(file_name, "r"):
            print("Found file " + file_name)
            pass
        return True
    except FileNotFoundError:
        return False


def load_yaml(file_name):  # load the config.yml file.
    """Called at program launch, this subroutine checks to see if the cofig file can be 
    written to and then if a FileNotFoundError is met the program resets the config file
    to how it should be. A note on security here: Sensitive data should be stored within
    a .env file or stored in global/system varibles. However, whilst developing the
    program I had to program on multiple devices cauing the sensitive login data to be lost.
    The data is pre-setup for easy quick running of the python file. """
    print("Attempting connection to " + file_name)
    try:
        with open(file_name, "r"):
            print("Successfully connected to " + file_name)
            pass
    except FileNotFoundError:
        print("Could not find file " + file_name + " Creating default configuration now")
        with open(file_name, "w+") as f:
            f.write("""
# HairPlanner configuration file.
# NOTE ON PLACEHOLDERS!
# Currently there are these placeholders,
# %%NAME%% - Gets attendees name
# %%BUSINESS%% - Gets Business Name
# %%DATE%% - Gets the attendees booking date in dd/mm/yyyy format
# Your personal HairDresser code. Can be changed to anything you want.
# NOTE! The whole line needs to be changed from the colon! The random letters at the end are to stop attackers
# (they can be deleted). 
code: ChangeMe_""" + str(uuid.uuid4()).replace("-", "") + """
business name: Hair Affair

# Admin account settings
# This is your account, this account will be able to modify customers
# and change booking slots! You can add multiple admin accounts
admin accounts:
  admin1:
    user: admin
    password: ChangeMe_""" + str(uuid.uuid4()).replace("-", "") + """
# admin2:
#   user: admin2
#   password: ChangeMe_""" + str(uuid.uuid4()).replace("-", "") + """
  cookie-response: """ + str(uuid.uuid4()).replace("-", "") + """
  # this will be checked to see if the account logged in is an admin account, like a password - don't share!

email:
  address: changeme@gmail.com
  app-password: AppPassword
# Email address and app-password to use when verifying emails.
# requires access to IMAP and SMTP. Gmail account recommended. Otherwise using SMTP protocol
# gmail: 2fa needs to be enabled to gain app-passwords

google calendar: # Google calendar intergration settings
    client-id: add_me
    client-secret: add_me
settings: 
    time-zone: Etc/UTC
    # only change if bookings are showing in strange places!
    # Time zone that you are in see https://en.wikipedia.org/wiki/List_of_tz_database_time_zones
    # for valid values
    location: The Moon
    # Location of your Salon, copy from google maps
    extra-attendees: ['your.other.business@email.here', 'and.another@email.here'] 
    # Add extra attendees to EVERY booking (managers)
    description: '''Your long description about how to get to your salon. You can use placeholders!''' 

# Advanced
password-security:
  salt: """ + str(os.urandom(128)) + """
  # the salt to apply to passwords.
  hash-iterations: 100000 
  # how many iterations of the sha-256 algorithm to use. Recommended = 100000 
  key-size: 128
  # length of key to return from hashing algorithm.
  
version: 0.5
# Version Number. Do not change!
# Hair Booking System Open Source and Beautiful - BEMZlabs""")
            pass
    with open(file_name, 'r') as f:
        yamlfile = yaml.safe_load(f)
    return yamlfile


def all_accounts():  # return all accounts within the database wrapped in a dict
    """ all_accounts() and all_dates() are practically the same, they just call different tables. When required the 
    program will attempt to get all data from a table within the database, and then convert the data into a python 
    readable dictionary.""" 
    connection = sql.connect("storage.db")
    c = connection.cursor()
    qu = "SELECT * FROM accounts"
    accounts = c.execute(qu)
    accounts_data = []
    for row in accounts:
        account = {"id": row[0], "pass": row[2], "email": row[3], "user": row[1], "active": row[4], "uuid": row[5]}
        accounts_data.append(account)
    return accounts_data


def all_dates():  # return all dates within the database wrapped in a dict
    dtnow = datetime.datetime.now().timestamp()
    connection = sql.connect("storage.db")
    c = connection.cursor()
    qu = "SELECT * FROM dates"
    dates = c.execute(qu)
    dates_data = []
    for row in dates:
        print(row)
        if int(row[2]) < int(dtnow):  # Remove any dates that are in the past.
            c.execute("DELETE from dates where id=?; ", (int(row[0]),))
            connection.commit()
            pass
        else:
            try:
                dates = {"id": row[0], "user": row[1], "date_start": row[2], "length": row[3], "price": row[4],
                         "desc": row[5], "products": ast.literal_eval(
                        row[6])}  # literal_eval is a way of getting raw data from SQL table, in this case its a list.
            except SyntaxError:
                dates = {"id": row[0], "user": row[1], "date_start": row[2], "length": row[3], "price": row[4],
                         "products": ast.literal_eval(row[5]), "desc": row[6]}
            dates_data.append(dates)
    return dates_data


def save_date_data(time_since_epoch, user, length, desc, price, products):  # validate data and save it to database
    dates = all_dates()
    for x in dates:
        datetime_time = datetime.datetime.fromtimestamp(int(x["date_start"]))
        minutes = datetime.timedelta(minutes=int(x["length"]))
        end = datetime_time + minutes
        end = end.timestamp()
        # This if statement checks to see if the two time varibles are in the past.  
        if not (int(time_since_epoch) > float(end) or int(time_since_epoch) < int(x["date_start"])): 
            # time invalid
            return False
        else:
            pass
    # when we get here, time should be valid
    with sql.connect('storage.db') as db:
        cursor = db.cursor()
        cursor.execute("""INSERT INTO dates (user, date_start, length, price, products, desc)
VALUES( ?, ?, ?, ?, ?, ?);""", (str(user), int(time_since_epoch), int(length), float(price), str(products), str(desc)))
        db.commit()
        cursor.close()
    return True


def save_data(table, user, passw, email, uuid):  # save account data within the database
    """Any data appended with this subroutine should be validated prior.""" 
    user = str(user)
    passw = str(passw)
    email = str(email)
    sql_create_accounts_table = """CREATE TABLE IF NOT EXISTS accounts (
                                        id INTEGER PRIMARY KEY,
                                        user text NOT NULL UNIQUE,
                                        pass text NOT NULL,
                                        email text NOT NULL UNIQUE,
                                        active integer NOT NULL,
                                        uuid text NOT NULL UNIQUE,
                                        UNIQUE(user,id, email)
                                    ) """
    sql_create_dates_table = """CREATE TABLE IF NOT EXISTS dates (
                                        id INTEGER PRIMARY KEY,
                                        user text NOT NULL,
                                        date_start INTEGER NOT NULL,
                                        length INTEGER NOT NULL,
                                        price FLOAT NOT NULL,
                                        desc text NOT NULL,
                                        products text NOT NULL
     ) """
    sqlite_insert_query = "INSERT INTO accounts (user, pass, email, active, uuid) VALUES (?, ?, ?, 0, ?);"
    try:
        with sql.connect("storage.db") as con:
            c = con.cursor()
            c.execute(sql_create_accounts_table)
            c.execute(sql_create_dates_table)
            c.execute(sqlite_insert_query, (user, passw, email, uuid))
            con.commit()
            c.close()
    except sql.IntegrityError:
        flash("That account already exists!", "error")
        return False
    return True


def get_user_info(user):  # find user within database and return their data, formatted [{RESULT1}, {RESULT2}]
    # This is similar to all_dates and all_accounts, however this only returns one user.
    connection = sql.connect("storage.db")
    c = connection.cursor()
    qu = "SELECT * FROM accounts WHERE user = ?"
    accounts = c.execute(qu, (user,))
    accounts_data = []
    for row in accounts:
        account = {"id": row[0], "pass": row[2], "email": row[3], "user": row[1], "active": row[4], "uuid": row[5]}
        accounts_data.append(account)
    return accounts_data


def edit_db(command, args):  # run a command within the database, and return its value
    conn = sql.connect("storage.db")
    c = conn.cursor()
    out = c.execute(command, args)
    conn.commit()
    c.close()
    conn.close()
    return out

# This decorator tells that the following subroutine should be treated as a web end-point.
@app.route("/handle_admin_email_data", methods=["POST"])  # handler for send_email.html
def handle_admin_email_data():
    name = str(request.form["name"]).split(" | ")[0]  # get rid of formatting from auto-selector.
    header = request.form["title"]
    content = request.form["body"]
    if not name == "ALL":  # check if we are seding to everyone in table
        if "@" in name:  # we are dealing with an email address
            email = name
        else:  # need to find the email of the account name
            user = get_user_info(name)[0]
            email = user["email"]
        try:
            send_email(email, header, content)
        except Exception as error:
            return flash("The email was not able to be sent. \n\n" + str(error), "error")
    else:  # we are dealing with EVERYONE
        try:
            acc = all_accounts()
            for x in acc:  # index through all emails within the database
                send_email(x["email"], header, content)
        except Exception as error:
            return flash("Some emails were not able to be sent. \n\n" + str(error), "error")
    return redirect(url_for("hub"))  # after all that redirect to hub


@app.route("/handle_reg_data", methods=["POST"])  # handler for registration data (register.html)
def handle_reg_data():
    """
    This subroutine will get data from a form on the previous page, validate, send a registration
    email and activate a link to verify the users account by appending a uuid v4 into a file.
    """
    n = request.form["name"]  # get form data
    email = request.form["email"]
    code = request.form["code"]
    password = request.form["pass"]
    vpassword = request.form["ppass"]
    common_passwords = open("common_passwords.txt", "r")
    common_passwords = common_passwords.readlines()
    cpass = []
    for x in common_passwords:
        cpass.append(str(x).replace("\n", ""))
    flag = False  # use this for veirfying security of password
    error = ''
    if len(password) < 8:  # requirements: Longer than 8 chars, contain lower + upper + numbers + symbols. NOT
        # Whitespace
        flag = True
        error = 'Password too short!'
        pass
    elif not re.search("[a-z]", password):  # using Regular Expressions
        flag = True
        error = 'Password must contain letters!'
        pass
    elif not re.search("[A-Z]", password):
        flag = True
        error = 'Password must contain UPPERCASE letters!'
        pass
    elif not re.search("[0-9]", password):
        flag = True
        error = 'Password must contain numbers!'
        pass
    elif not re.search("[_@£$%&()]", password):
        flag = True
        error = 'Password must contain Special characters (_@£$%&)!'
        pass
    elif re.search("\s", password):
        error = 'Password must NOT contain spaces!'
        flag = True
        pass
    elif password in cpass:  # check through the 1,000,000 most common passwords and check for user password.
        error = 'Password is too common!'
        flag = True
        pass
    elif re == vpassword:  # the password and verfy password must match
        error = 'Password must match!'
        flag = True
        pass
    elif code != str(CONFIG["code"]):  # stop random people making an account
        error = 'Not a valid Hair Dresser code!'
        flag = True
        pass
    if flag:  # if any checks failed
        flash(error, 'error')
        return redirect(url_for('register', error=error, business_name=BUSINESS))
    else:
        iterations = CONFIG["password-security"]["hash-iterations"]  # get data required to encrypt data
        salt = SSALT
        key = hashlib.pbkdf2_hmac('sha256', password.encode("utf-8"), salt,
                                  int(iterations))  # generate their encyrpted password
        idd = str(uuid.uuid4()).replace("-", "")  # generate a uuid for the account and strip any "-"'s
        test = save_data("accounts", n, key, email, idd)  # save it all into the database
        if not test:
            flash('The account already exists!', 'error')
            return redirect(url_for('register', error=error, business_name=BUSINESS))
        with open("non-active-accounts", 'w') as f:  # open a tempory file and write the uuid into it
            f.write(idd + "\n")
        f.close()
        head = "Your Verification code for {}.".format(BUSINESS)
        vcode = "Hello " + str(n) + ".\nPlease click this link to start booking!\n" + str(
            request.root_url) + "verify?key=" + str(idd) + "\n\nThanks,\n " + str(BUSINESS) + " admin team."
        content = vcode  # work around otherwise get strange error on repl.it
        error = send_email(email, head, content)  # send email, check for errors
        if error:
            flash(error, 'error')
            return redirect(url_for("register", business_name=BUSINESS, error=error))
        flash("Account Created successfully, please check you email to verify!", "success")
        return redirect(url_for('login'))


@app.route('/admin/send_email')  # admin send email page
def admin_send_email():
    if request.cookies.get('uID') == CONFIG["admin accounts"]["cookie-response"]:  # check if user logged in is the
        # admin account
        accounts = all_accounts()
        names = []
        emails = []
        for account in accounts:
            names.append(account["user"])
            emails.append(account["email"])
        return render_template("send_email.html", business_name=BUSINESS, len=len(names), users=names, emails=emails)
    else:
        return redirect(url_for("index"))


@app.route('/admin/bookings')
def admin_bookings():
    if request.cookies.get('uID') == CONFIG["admin accounts"]["cookie-response"]:
        acc = all_accounts()
        da = all_dates()
        name = []
        date = []
        notes = []
        est_time = []
        i = 0
        plen = []
        products = []
        for x in da:  # run through all dates
            name.append(x["user"])  # unpack users into seperate lists
            date.append(datetime.datetime.fromtimestamp(x["date_start"]).strftime(
                "%d-%m-%Y %H:%M"))  # using datetime.fromtimestamp to convert from UNIX time to a datetime timestamp,
            # then converting to dd-mm-YYYY HH:MM format
            notes.append(x["desc"])
            plen.append(len(x["products"]))
            products.append(x["products"])
            est_time.append(
                str(datetime.timedelta(seconds=x["length"])))  # convert minutes to a datetime.timedelta object
            i += 1
        return render_template("AllBookings.html", len=i, name=name, time=date, notes=notes, est_time=est_time,
                               business_name=BUSINESS, current_user="Admin", user="Admin", plen=plen, products=products)
    else:
        return redirect(url_for('index'))


@app.route('/admin/remove_dates')
def remove_dates():  # wipe all dates from admin panel
    if request.cookies.get("uID") == CONFIG["admin accounts"]["cookie-response"]:
        wipe_dates()
        return "<script>window.history.back()</script>"  # this JavaScript presses the browsers back button
    else:
        return "<script>window.history.back()</script>"


@app.route("/handle_booking_data", methods=['POST'])  # backend for handeling booking data
def handle_booking_data():
    dat = request.form["udate"]  # get data from form
    tim = request.form["utime"]
    desc = request.form["comments"]
    SelectedServices = []
    SelectedSerivesNames = []
    for x in range(len(CONFIG["products"])):  # because the checkboxes are generated using Jinja templates,
        # we set a name then an index to the id. This loop is just storing the name of each product to True or False
        # reguardless if that product was selected.
        if request.form.get("selection" + str(x)):
            SelectedServices.append(True)
            SelectedSerivesNames.append(CONFIG["products"][x][0])
        else:
            SelectedServices.append(False)
    # work out estimated time and price
    TimeTotal = 0
    PriceTotal = 0.0
    for x in range(len(CONFIG["products"])):  # go through each product
        if SelectedServices[x]:  # if the product is selected
            TimeTotal += CONFIG["products"][x][2]  # add that products estimated time to the total
            PriceTotal += CONFIG["products"][x][1]  # add price to total
    # find if there are any clashes with date and time already in database.
    dat = dat.split("-")  # format the date
    tim = tim.split(":")
    y = int(dat[0])
    m = int(dat[1])
    d = int(dat[2])
    h = int(tim[0])
    mi = int(tim[1])
    timestamp = datetime.datetime(y, m, d, h, mi).timestamp()  # convert time to datetime.datetime timestamp
    current_timestamp = datetime.datetime.now().timestamp()  # get the current UNIX time
    out = False
    if request.cookies.get('uID') == CONFIG["admin accounts"]["cookie-response"]:  # if an admin added this date
        # check if time is in the future
        if int(timestamp) > int(current_timestamp):
            out = save_date_data(timestamp, "Admin", TimeTotal, desc, PriceTotal, SelectedSerivesNames)  # set
            # the name to "Admin"
        else:
            return flash("The provided date is in the past. Please enter a valid date and time!", "error")
    else:
        if int(timestamp) > int(
                current_timestamp):  # because unix timestamps are scalar and a real number , you can do this
            out = save_date_data(timestamp, str(request.cookies.get('uID')), TimeTotal,
                                 desc, PriceTotal, SelectedSerivesNames)  # use the loged in users name
        else:
            info = "The provided date is in the past. Please enter a valid date and time!"
            flash(info, "error")
            return (redirect(url_for("book")))
    if not out:
        info = "There is already a booking for this time, please select a different time slot!"
        flash(info, "error")
        return (redirect(url_for("book")))
    ct = datetime.datetime(y, m, d, h, mi)
    ctn = ct + relativedelta(minutes=TimeTotal)
    ctn = ctn.isoformat()
    ctf = ct.isoformat()
    try:
        user = get_user_info(str(request.cookies.get('uID')))[0]  # find the user and return with their data
    except IndexError:
        user = {"email": CONFIG["email"][
            "address"]}  # the email is only used currently, so simulate what get_user_info would return.
    desc = CONFIG["google calendar"]["settings"]["description"] + "\n-------------------------------------------" \
                                                                  "----------------------------------------------" \
                                                                  "\n User Comments:\n" + desc
    event = {  # Creating the information that Google Calendar API requests
        'summary': render_text(CONFIG["google calendar"]["settings"]["title"]),
        'location': CONFIG["google calendar"]["settings"]["location"],
        'description': render_text(desc),
        'start': {
            'dateTime': ctf,
            'timeZone': CONFIG["google calendar"]["settings"]["time-zone"],
        },
        'end': {
            'dateTime': ctn,
            'timeZone': CONFIG["google calendar"]["settings"]["time-zone"],
        },
        'recurrence': [],
        'attendees': [
            {'email': CONFIG["email"]["address"]},
            {'email': user["email"]},
        ],
        'reminders': {
            'useDefault': True,
            'overrides': [],
        },
    }
    try:
        event = GOOGLE.events().insert(calendarId='primary',
                                       body=event).execute()  # get google's events, write it, then send to google
        
    # calendar.
    except AttributeError:
        info = "Google accounts not set up!"
        flash(info, "info")
        return redirect(url_for('hub'))
    info = "Booking successfully created"
    flash(info, "info")
    return redirect(url_for('hub'))  # finally return to hub.


@app.route('/handle_data', methods=['POST'])  # backend handler for login data
def handle_data():
    u = request.form["user"]  # these wont need to be encrypted through client, as SSL encryption will be served through
    p = request.form["pass"]  # HTTPS in the browser.
    # check if account is admin
    admin = CONFIG["admin accounts"]
    for x in admin:
        account = admin[x]
        if account == CONFIG["admin accounts"]["cookie-response"]:
            break  # this item is not an account
        if request.form.get("PersistantLogin"):  # if cookies enabled;
            if (account["user"] == u) and (account["password"] == p):
                resp = make_response(
                    redirect(url_for('hub')))  # create a packet we can send to the web browser with a cookie included
                expire_date = datetime.datetime.now()
                expire_date = expire_date + relativedelta(years=1)  # add one year onto the datetime.datetime object
                resp.set_cookie('uID', str(CONFIG["admin accounts"]["cookie-response"]),
                                expires=expire_date, secure=True, httponly=True)  # inject the cookie into the packet
                return resp  # send to the client
        if (account["user"] == u) and (account["password"] == p):  # the user did not check stay logged in
            resp = make_response(redirect(url_for('hub')))
            resp.set_cookie('uID', str(CONFIG["admin accounts"][
                                           "cookie-response"]), secure=True,
                            httponly=True)  # just create the cookie, the browser will delete
            # the cookie after the session is closed.
    # normal account
    iterations = CONFIG["password-security"]["hash-iterations"]
    accounts = all_accounts()
    salt = SSALT
    key = hashlib.pbkdf2_hmac('sha256', p.encode('utf-8'), salt,
                              int(iterations))  # we need to encrypt the pass word to check its key against the user
    # in the database

    for x in accounts:  # index through accounts because dictionaries are weird.
        if str(u) == str(x["email"]):
            if str(key) == str(x["pass"]):
                if x["active"] == 1:
                    if request.form.get("PersistantLogin"):  # if cookies enabled
                        resp = make_response(redirect(url_for('hub')))
                        expire_date = datetime.datetime.now()
                        expire_date = expire_date + relativedelta(years=1)
                        resp.set_cookie('uID', str(x["user"]), expires=expire_date, secure=True, httponly=True)
                        return resp
                    else:
                        resp = make_response(redirect(url_for('hub')))
                        resp.set_cookie('uID', str(x["user"]), secure=True, httponly=True)
                        return resp
                else:  # the account has not verified their email.
                    error = 'This account is not active yet. Please check your emails!'
                    flash(error, "error")
                    return redirect(url_for("login", error=error, business_name=BUSINESS))
    error = 'Incorect login details!'  # otherwise the user has entered invalid data
    flash("Incorrect login information!", "error")
    return redirect(url_for("login", error=error, business_name=BUSINESS))


@app.route('/register')
def register():  # main register page
    if request.cookies.get('uID'):  # check if user is logged in already
        return redirect(url_for('hub'))
    else:
        return render_template("register.html", business_name=BUSINESS)


@app.route('/book')
def book():  # booking page
    if request.cookies.get('uID'):
        return render_template("book.html", business_name=BUSINESS, plen=len(CONFIG["products"]),
                               products=CONFIG[
                                   "products"], user=request.cookies.get(
                'uID'))  # get all products and length of the products so the renderer can generate a checkbox for
        # each product.
    else:
        return redirect(url_for('index'))


@app.route('/login')
def login():  # login page
    if request.cookies.get('uID'):  # check if logged in
        return redirect(url_for('hub'))
    else:
        return render_template("login.html", business_name=BUSINESS)


@app.route('/logout')
def logout():  # log out paage
    if request.cookies.get('uID'):  # check if user is logged in
        resp = make_response(redirect(url_for('index')))  # create a redirect packet
        t = int(str(time.time() // 1).replace(".0",
                                              "")) + 5  # overwite the cookie to set its expiry to 5 seconds after
        # current time
        resp.set_cookie('uID', '', expires=t)  # "deletes" the cookie
        return resp  # send to client
    else:
        return redirect(url_for('index'))


@app.route('/admin/hub')
def admin_hub():  # admin hub settings
    try:
        if request.cookies.get('uID') == CONFIG["admin accounts"]["cookie-response"]:  # check if admin is logged in
            bookings = all_dates()
            for_time = []
            i = 0
            for sdate in bookings:
                for_time.append(datetime.datetime.utcfromtimestamp(sdate["date_start"]).strftime('%A %d %B %H:%M'))
                i += 1
            return render_template("hub.html", business_name=BUSINESS, user="Admin", time=for_time, len=i, admin=True)
        else:
            return redirect(url_for("index"), code=401)
    except Exception:
        return render_template("error.html", business_name=BUSINESS, error=traceback.format_exc())


@app.route('/delete_account', methods=['POST'])
def delete_account():
    if request.cookies.get('uID') == CONFIG["admin accounts"]["cookie-response"]:
        return flash("Admin Accounts cannot delete their accounts! Please edit config.yml to remove this account.",
                     "error")
    else:
        user = get_user_info(request.cookies.get("uID"))[0]
        with sql.connect('storage.db') as db:  # update the account to an active account
            cursor = db.cursor()
            cursor.execute("DELETE FROM dates WHERE user = ?;", (user["user"],))
            cursor.execute("DELETE FROM accounts WHERE uuid = ?;", (user["uuid"],))
            db.commit()
            cursor.close()
        resp = make_response(redirect(url_for('index')))  # create a redirect packet
        t = int(str(time.time() // 1).replace(".0",
                                              "")) + 5  # overwite the cookie to set its expiry to 5 seconds after
        # current time
        resp.set_cookie('uID', '', expires=t)  # "deletes" the cookie
        return resp  # send to client


@app.route('/delete/bookings')
def delete_personal_bookings():
    user = request.cookies.get('uID')
    with sql.connect('storage.db') as db:
        cursor = db.cursor()
        cursor.execute("DELETE FROM dates WHERE user = ?;", (user,))
        db.commit()
        cursor.close()
    return redirect(url_for("hub"))


@app.route('/hub')
def hub():  # main page
    try:
        if request.cookies.get('uID') == CONFIG["admin accounts"]["cookie-response"]:
            # if admin logged in forward to admin_hub
            return redirect(url_for("admin_hub"))
        if request.cookies.get('uID'):  # if normal account
            user = request.cookies.get('uID')
            ct = datetime.datetime.now()
            bookings = all_dates()
            for_time = []
            price = []
            products = []
            time_len = []
            plen = []
            i = 0
            for sdate in bookings:
                if sdate["user"] == user:
                    for_time.append(datetime.datetime.utcfromtimestamp(sdate["date_start"]).strftime('%A %d %B %H:%M'))
                    price.append(sdate["price"])
                    products.append(sdate["products"])
                    plen.append(len(sdate["products"]))
                    z = datetime.timedelta(minutes=sdate["length"])  # why does timedelta not have .strftime? Python
                    # please fix
                    total_seconds = int(z.total_seconds())  # Roundabout way of converting minutes into Hours +
                    # minutes because of above comment.
                    hours, remainder = divmod(total_seconds, 60 * 60)
                    minutes, seconds = divmod(remainder, 60)
                    if hours == 0:
                        time_len.append(str(minutes) + " minutes")
                    else:
                        time_len.append(str(hours) + " hours and " + str(minutes) + " minutes")
                    i += 1
                else:
                    pass
            return render_template("hub.html", business_name=BUSINESS, user=user, time=for_time, len=i, plen=plen,
                                   price=price, product=products, currency=CONFIG["currency"], time_format=time_len)
        else:
            return redirect(url_for('login'))  # not logged in
    except Exception:
        return render_template("error.html", business_name=BUSINESS, error=traceback.format_exc())


@app.route('/')  # just forward the index page " / " to hub.html if logged in, else show landing page
def index():
    try:
        if request.cookies.get('uID'):
            return redirect(url_for('hub'))
        else:
            return render_template("index.html", business_name=BUSINESS)
    except Exception:
        render_template("error.html", business_name=BUSINESS, error=traceback.format_exc())


@app.route('/verify')
def verify():  # only used within email verification
    try:
        if request.args.get('key'):  # there is a key attached to every verification email
            key = request.args.get('key')  # get the key from link
            fkey = str(key) + "\n"  # add a new line to the end
            with open("non-active-accounts", "r") as f:  # open the file and check for it in the non active accounts
                keysraw = f.readlines()
                for x in range(len(keysraw)):
                    if keysraw[x] == fkey:
                        keysraw[x] = ""  # delete the temp key
                    f.close()
            with open("non-active-accounts", "w") as f:
                f.writelines(keysraw)  # re-write the new keys
                f.close()  # close and save the file
            accounts = all_accounts()
            for x in accounts:
                if x["uuid"] == key:  # find the account in the database
                    # this is the account
                    with sql.connect('storage.db') as db:  # update the account to an active account
                        cursor = db.cursor()
                        cursor.execute("UPDATE accounts SET active = 1 WHERE uuid = ?;", (key,))
                        db.commit()
                        cursor.close()
                    return "Account Successfully activated.<script>window.onload = window.close();</script>"
                    # close the page
                else:
                    pass
            return redirect(url_for("index"))  # otherwise redirect to index
        else:
            return redirect(url_for('login'))
    except Exception:
        return render_template("error.html", business_name=BUSINESS, error=traceback.format_exc())


@app.route("/settings")
def settings():
    try:
        if request.cookies.get('uID') == CONFIG["admin accounts"]["cookie-response"]:
            flash("Admin Accounts can not access this page for now.", "error")
            return redirect(url_for("hub"))
        if request.cookies.get('uID'):
            user = get_user_info(str(request.cookies.get('uID')))[0]
            fname = str(user["user"]).split(" ")[0]
            lname = str(user["user"]).split(" ")[1]
            return render_template("profile.html", business_name=BUSINESS, email=user["email"], first_name=fname,
                                   last_name=lname, current_user=str(request.cookies.get('uID')),
                                   user=request.cookies.get('uID'))
        else:
            return redirect(url_for('login'))
    except Exception:
        return render_template("error.html", business_name=BUSINESS, error=traceback.format_exc())


@app.route("/change_user_info", methods=['POST'])
def change_user_info():
    fname = request.form["first_name"]
    lname = request.form["last_name"]
    name = fname + " " + lname
    with sql.connect('storage.db') as db:  # update the account to an active account
        cursor = db.cursor()
        try:
            cursor.execute("""UPDATE accounts SET user = ? WHERE user = ?;""",
                           (str(name), str(request.cookies.get('uID'))))
        except sql.IntegrityError:
            return flash("The name " + str(name) + " is currently reserved by another user!", "error")
        db.commit()
        cursor.close()
    resp = make_response(redirect(url_for('settings')))
    resp.set_cookie('uID', str(name), secure=True, httponly=True)
    return resp


@app.route("/calendar")
def calendar():
    try:
        return redirect("https://calendar.google.com")  # forward to calendar.google.com
    except Exception:
        return render_template("error.html", business_name=BUSINESS, error=traceback.format_exc())


@app.errorhandler(404)
def error_404(e):  # oh, no
    if request.cookies.get('uID'):
        return render_template("404.html", business_name=BUSINESS, user=request.cookies.get('uID'),
                               current_user=str(request.cookies.get('uID'))), 404
    else:
        return render_template("404.html", business_name=BUSINESS), 404


@app.errorhandler(HTTPException)
def error(e):  # bigger oh no
    return render_template("error.html", business_name=BUSINESS, error=e), e


if __name__ == '__main__':  # on start-up
    CWD = os.getcwd()
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    generate_database()
    if not verify_file("setup"):
        print(
            "You need to setup your Keys for Google calendar sync please see this website: "
            "https://console.developers.google.com/ for more info.")
        url = pyqrcode.create('https://console.developers.google.com/')
        print(url.terminal(quiet_zone=1))
        open("setup", "w").close()
        input("Press enter to continue.")
        raise Exception("credentials.json is not found or invalid.\nPlease see the above website for more info.")
    print("Welcome! The Current Working Directory is " + CWD)
    print("Check for updates...")
    if update():
        url = pyqrcode.create('https://github.com/BEMZ01/Hair-Booking-System-Public/')
        print("Updates found!\nPlease update at https://github.com/BEMZ01/Hair-Booking-System-Public\n\n" + str(
            url.terminal(quiet_zone=1)) + "\n\nStarting in 15 seconds.")
        time.sleep(15)
    GOOGLE = google_login()
    if not GOOGLE:
        GOOGLE = google_login()  # get google login
    if not verify_file("config.yml"):
        print(
            """\n! ! ! ! !\nThe config.yml file was not found. It has been generated for you. Please check through 
            this file and change the passwords within it. The default passwords can be easily guessed!\n! ! ! ! !\n""")
        input("Press ENTER to continue.\n> ")  # config file was not found, shows a message to the console.
    else:
        pass
    CONFIG = load_yaml("config.yml")  # load global variables
    SSALT = bytes(CONFIG["password-security"]["salt"], "utf-8")
    BUSINESS = CONFIG["business name"]
    print("Ready!\n\nStarting Flask")
    app.secret_key = SSALT
    app.run("0.0.0.0", 8080, debug=True)  # start the flask web server on port 8080
