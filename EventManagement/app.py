from flask import Flask, url_for, redirect, request, render_template, flash, session
from wtforms import Form, StringField, TextAreaField, BooleanField, PasswordField, validators
from config import Config
from wtforms.fields.html5 import EmailField
from passlib.hash import sha256_crypt
from functools import wraps
from datetime import date, datetime
from flask_mysqldb import MySQL
from dateutil.parser import parse
from werkzeug.utils import secure_filename
import os


UPLOAD_FOLDER = './static/img'
app = Flask(__name__)
app.config.from_object(Config)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'dbuser'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'mydb'
# init MySQL
mysql = MySQL(app)


@app.route('/')
@app.route('/index')
def index():
        return render_template('home.html')

# Check if user logged in 
def is_logged_in(f):
        @wraps(f)
        def wrap(*args, **kwargs):
                if 'logged_in' in session:
                        return f(*args, **kwargs)
                else:
                        flash("Unauthorized, Please Login", 'danger')
                        return redirect(url_for('login'))
        return wrap


class RegisterForm(Form):
        name = StringField('Name', [validators.DataRequired(), validators.Length(min=1, max=50)])
        email = EmailField('Email', [validators.DataRequired(), validators.Length(min=6, max=50)])
        phone = StringField('Phone', [validators.DataRequired(), validators.Length(min=10, max=10)])
        college = StringField('College', [validators.DataRequired(), validators.Length(min=4, max=50)])
        password = PasswordField('Password', [validators.DataRequired(),
        validators.EqualTo('confirm', message='Passswords do not match')])
        confirm = PasswordField('Confirm Password')
               
@app.route('/register', methods=['GET', 'POST'])
def register():
        form = RegisterForm(request.form)
        if request.method == 'POST' and form.validate():
                name = form.name.data   
                email = form.email.data
                phone = form.phone.data
                college = form.college.data
                password = sha256_crypt.encrypt(str(form.password.data))

                # Create cursor
                cursor = mysql.connection.cursor()
                cursor.execute("SELECT * From users where email = %s", [email])
                dd = cursor.fetchall()
                if len(dd) == 0:
                        cursor.execute("INSERT INTO users(name, email, password, phone, college) VALUES(%s, %s, %s, %s, %s)", (name, email, password, phone, college))
                else:
                        flash("Email already registered", 'danger')
                        return render_template('register.html', form=form)        
                mysql.connection.commit()
                cursor.close()

                flash('You are now registered and can log in', 'success')
                return render_template('login.html')
        return render_template('register.html', form=form)


@app.route('/login', methods = ['GET', 'POST'])
def login():
        return render_template('login.html', title="Login")

@app.route('/login__', methods=['GET', 'POST'])
def login__():        
        if request.method == 'POST':
                email = request.form['email']
                password_candidate = request.form['password']
                cursor = mysql.connection.cursor()
                result = cursor.execute("SELECT * FROM users WHERE email = %s", [email])
                if result > 0:
                        data = cursor.fetchone()
                        password = data[1]
                        if sha256_crypt.verify(password_candidate, password):
                                session['logged_in'] = True
                                session['email'] = email
                                user = email[0:email.index('@')]
                                session['username'] = user
                                flash('You are now logged in', 'success')
                                return redirect(url_for('dashboard'))
                        else:
                                error = "Passwords not matched"
                                return render_template('login.html', error = error)
                        cursor.close()
                else:
                        error = "Email Address not found"
                        return render_template('login.html', error = error)
        else:
                return render_template('login.html', title="Login")

@app.route('/forgotpassword', methods = ['GET', 'POST'])
def forgotpassword():
        return render_template('forgotpassword.html', title = "Forgot Password")

@app.route('/passwordupdate', methods=['POST'])
def passwordupdate():
        email_g = request.form['email']
        password_g = request.form['password']
        password_g = sha256_crypt.encrypt(str(password_g))
        cursor = mysql.connection.cursor()
        cursor.execute("Update users SET password = %s WHERE email = %s", [password_g, email_g])
        mysql.connection.commit()
        flash('Your password has been updated', 'success')
        return render_template('login.html', title="Login")

@is_logged_in
@app.route('/logout', methods=['GET', 'POST'])
def logout():
        session.clear()
        flash('You are now logged out', 'success')
        return redirect(url_for('login'))

class Contact_Us_Form(Form):
        name = StringField('Name', [validators.DataRequired(), validators.Length(min=1, max=50)])
        email = EmailField('Your-Email', [validators.DataRequired(), validators.Length(min=6, max=50)])
        body = TextAreaField('Body', [validators.DataRequired(), validators.Length(min=10)])
   
@app.route('/contact_us', methods = ['GET', 'POST'])
def contact_us():
        form = Contact_Us_Form(request.form)
        if request.method == 'POST' and form.validate():
                name = form.name.data
                email = form.email.data
                body = form.body.data
                #print(name, email, body)

                flash('Your response has been registered', 'success')
                return render_template('home.html')
        
        return render_template("contact_us.html", title="Contact Us", form=form)

@app.route('/dashboard', methods=['GET', 'POST'])
@is_logged_in
def dashboard():
        email = session['email']
        user = email[0:email.index('@')]
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT email, admin_flag From users")
        users1 = cursor.fetchall()
        users = []
        users2 = []
        for u in users1:
                if u[1] != 1:
                        users.append(u[0])
                if u[1] == 1 and u[0] != "admin@admin":
                        users2.append(u[0])
        #print(users2)
        '''
                flag = 0 for normal users
                flag = 1 implies user is admin but hasn't added a festival yet, so he is shown add_festival button
                flag = 2 implies user is admin and has added a festival, so will be shown only add_event button
                flag = 100 implies user is super_admin and gets all buttons
        '''
        flag = 0
        cursor.execute("SELECT admin_flag From users where email = %s", [email])
        is_admin = cursor.fetchall()
        festival_name = ""
        if is_admin[0][0] == 1:
                cursor.execute("SELECT * from festivals where admin_festival = %s", [email])
                dd1 = cursor.fetchall()
                if len(dd1) != 0:
                        flag = 2
                        festival_name = dd1[0][0]
                else:
                        flag = 1
        if user == "admin":
                flag = 100
        #print(flag)
        cursor.execute("SELECT festival_name from festivals")
        pp = cursor.fetchall()
        pp_final = []
        for p in pp:
                pp_final.append(p[0])
        
        return render_template('dashboard.html', title="Dashboard", user = email, users = users, flag = flag, email = email, festival_name = festival_name, users2 = users2, festivals = pp_final)

@app.route('/display_festivals')
def display_festivals():
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * From festivals")
        result = cursor.fetchall()
        festivals_list = []
        for festival in result:
                temp_dict = {}
                temp_dict['festival_name'] = festival[0]
                temp_dict['festival_start_date'] = festival[1]
                temp_dict['festival_end_date'] = festival[2]
                temp_dict['college_name'] = festival[3]
                temp_dict['admin_name'] = festival[5]
                if parse(temp_dict['festival_end_date']) >= datetime.today():
                        festivals_list.append(temp_dict)
        #print(festivals_list)
        festivals_list = sorted(festivals_list, key = lambda i : i['festival_start_date'])
        cc = 1
        for f in festivals_list:
                f['No'] = cc
                cc = cc + 1
        #print(festivals_list)

        return render_template('display_festivals.html', title="Festivals", festivals_list = festivals_list)

@app.route('/add_festival', methods=['GET', 'POST'])
@is_logged_in
def add_festival():
        try :
                fest_name_given = request.form['festival_name']
                fest_sd_given = request.form['festival_start_date']
                fest_ed_given = request.form['festival_end_date']
                college_name = request.form['college_name']
                user_name = request.form['user_name']
        except :
                pass
        # Create mysql cursor
        cursor = mysql.connection.cursor()
        f_start = parse(fest_sd_given)
        f_end = parse(fest_ed_given)
        #print(type(f_start))        
        
        if f_end < datetime.today() or f_start < datetime.today() or f_end < f_start:
                flash("Invalid Dates entered, Please Enter Future Dates", 'danger')
                return render_template('dashboard.html', title="Dashboard", user = session['email'])
        
        if user_name == 'admin@admin':
                cursor.execute("INSERT INTO festivals(festival_name, festival_start_date, festival_end_date, college_name) VALUES(%s, %s, %s, %s)", (fest_name_given, fest_sd_given, fest_ed_given, college_name))
                mysql.connection.commit()
        else:
                cursor.execute("SELECT * From festivals where admin_festival = %s", [user_name])
                dd = cursor.fetchall()
                if len(dd) == 0:
                        cursor.execute("INSERT INTO festivals(festival_name, festival_start_date, festival_end_date, college_name, admin_festival) VALUES(%s, %s, %s, %s, %s)", (fest_name_given, fest_sd_given, fest_ed_given, college_name, user_name))
                        mysql.connection.commit()
                else:
                        cursor.close()
                        flash("You cannot add another festival", "danger")
                        return render_template('dashboard.html', title="Dashboard", user = session['username'])        
        cursor.close()
        flash("Your festival has been entered in the database", 'success')
        return render_template('dashboard.html', title="Dashboard", user = session['email'])

@app.route('/remove_festival', methods=['GET', 'POST'])
@is_logged_in
def remove_festival():
        f_name_r = request.form['festival_name_r']
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE From festivals where festival_name = %s", [f_name_r])
        cursor.execute("DELETE From festival_events where festival_name = %s", [f_name_r])
        cursor.execute("DELETE From users_register where festival_name = %s", [f_name_r])
        mysql.connection.commit()
        flash("Your festival has been removed from the database", 'danger')
        return render_template('dashboard.html', title="Dashboard", user = session['email'])

@app.route('/add_event', methods=['GET', 'POST'])
@is_logged_in
def add_event():
        festival_name_given = request.form['festival_name']
        start_date_given = request.form['start_date']
        end_date_given = request.form['end_date']
        event_name_given = request.form['event_name']
        slots = request.form['slots']
        e_start = parse(start_date_given)
        e_end = parse(end_date_given)

        if e_start < datetime.today() or e_end < datetime.today() or e_start > e_end:
                flash("Invalid Dates entered, Please Enter Future Dates", 'danger')
                return render_template('dashboard.html', title="Dashboard", user = session['email'])
        
        # Create mysql cursor
        cursor = mysql.connection.cursor()  
        cursor.execute("INSERT INTO festival_events(festival_name, event_name, start_date, end_date, slots, seats_left) VALUES(%s, %s, %s, %s, %s, %s)", (festival_name_given, event_name_given, start_date_given, end_date_given, slots, slots))
        mysql.connection.commit()
        cursor.close()
        flash("Your event has been entered in the database", 'success')
        return render_template('dashboard.html', title="Dashboard", user = session['email'])


@app.route('/display_festival/<string:festival_name>')
def display_movie(festival_name):
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * From festival_events where festival_name = %s", [festival_name])
        results = cursor.fetchall()
        events_list = []
        j = 1
        for event in results:
                temp_dict = {}
                temp_dict['No'] = event[4]
                temp_dict['festival_name'] = event[0]
                temp_dict['event_name'] = event[1]
                temp_dict['start_date'] = event[2]
                temp_dict['end_date'] = event[3]
                temp_dict['slots'] = event[5]
                cursor.execute("SELECT * From users_register where festival_name = %s && event_name = %s", [festival_name, event[1]])
                qq = cursor.fetchall()
                temp_dict['seats_left'] = event[5] - len(qq)
                events_list.append(temp_dict)
        cursor.execute("SELECT admin_festival From festivals where festival_name = %s", [festival_name])
        dd2 = cursor.fetchall()
        admin_festival = dd2[0][0]
        cursor.close()
        return render_template('display_festival.html', title=festival_name, events_list = events_list, festival_name = festival_name, admin_festival = admin_festival)

@app.route('/about', methods=['GET', 'POST'])
def about():
        return render_template("about.html", title="About Page")

@app.route('/book_show/<int:show_id>', methods=['GET', 'POST'])
def book_show(show_id):
        if('logged_in' not in session):
                flash("Your must login first", 'danger')
                return render_template('login.html', title="Login")
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * From festival_events where id = %s", [show_id])
        results = cursor.fetchone()
        cursor.execute("SELECT admin_festival from festivals where festival_name = %s", [results[0]])
        de1 = cursor.fetchall()
        admin_festival = de1[0][0]
        if admin_festival ==  session['email'] or session['email'] == 'admin@admin':
                flag = True
        else:
                flag = False
        return render_template('book.html', title = "Booking Page", festival_name = results[0], event_name = results[1], flag = flag, email = session['email'])

@app.route('/confirm_booking', methods=['GET', 'POST'])
def confirm_booking():
        if('logged_in' not in session):
                flash("Your must login first", 'danger')
                return render_template('login.html', title="Login")
        event_name_given = request.form['event_name']
        festival_name_given = request.form['festival_name']
        username_given = request.form['username']
        email_given = request.form['email']
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * from users_register where festival_name = %s && event_name = %s && email = %s", [festival_name_given, event_name_given, email_given])
        re = cursor.fetchall()
        if len(re) == 0:
                cursor.execute("SELECT seats_left from festival_events where festival_name = %s && event_name = %s", [festival_name_given, event_name_given])
                de = cursor.fetchall()
                if de[0][0] == 0:
                        flash("No more slots left", 'danger')
                        return render_template('dashboard.html', title="Dashboard", user=session['email'])
                else:
                        cursor.execute("INSERT INTO users_register(festival_name, event_name, username, email) VALUES(%s, %s, %s, %s)", (festival_name_given, event_name_given, username_given, email_given))
                        new_val = de[0][0] - 1
                        cursor.execute("Update festival_events SET seats_left = %s Where festival_name = %s && event_name = %s", [new_val, festival_name_given, event_name_given])
                        mysql.connection.commit()
                        cursor.close()
        else:
                flash("Email ID already registered", 'danger')
                cursor.close()
                return render_template('dashboard.html', title="Dashboard", user = session['email'])
        flash("Your have been successfully registered", 'success')
        return render_template('dashboard.html', title="Dashboard", user = session['email'])

@app.route('/add_admin', methods=['GET', 'POST'])
def add_admin():
        user_selected =  request.form['Users']
        cursor = mysql.connection.cursor()
        cursor.execute("Update users SET admin_flag = '1' Where email = %s", [user_selected])
        mysql.connection.commit()
        cursor.close()
        flash(user_selected + " is added as an admin", 'success')
        return render_template('dashboard.html', title='Dashboard', user=session['email'])

@app.route('/remove_admin', methods=['GET', 'POST'])
def remove_admin():
        user_selected =  request.form['Users2']
        cursor = mysql.connection.cursor()
        cursor.execute("Update users SET admin_flag = '0' Where email = %s", [user_selected])
        mysql.connection.commit()
        cursor.close()
        flash(user_selected + " is no longer an admin", 'success')
        return render_template('dashboard.html', title='Dashboard', user=session['email'])


@app.route('/show_registerd_users', methods=['GET', 'POST'])
def show_registerd_users():
        festival_name = request.form['festival_name']
        event_name = request.form['event_name']
        #print(festival_name, event_name)
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * From users_register where festival_name = %s && event_name = %s", [festival_name, event_name])
        dd4 = cursor.fetchall()
        dfinal = []
        cc = 1
        for u in dd4:
                dt = {}
                dt['no'] = cc
                cc = cc + 1
                dt['username'] = u[2]
                dt['email'] = u[4]
                dfinal.append(dt)
        return render_template('show_registered_users.html', title="Registered_Users", festival_name=festival_name, event_name=event_name, users_list = dfinal)

@app.route('/images', methods = ["GET", "POST"])
def images():
        images = os.listdir('./static/img') 
        return render_template('images.html', title = "Images", images = images)

@app.route('/add_images', methods = ['GET' , 'POST'])
def add_images():
        file = request.files['file']
        #filename = secure_filename(file.filename)
        filename = file.filename
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        flash('DOne')
        images = os.listdir('./static/img')
        return render_template('images.html', title = "Images", images = images)



if __name__ == "__main__":
        app.run(debug=True, threaded=True)
