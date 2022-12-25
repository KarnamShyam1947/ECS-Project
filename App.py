from flask import Flask, render_template, request, redirect, url_for, send_from_directory
from werkzeug.exceptions import RequestEntityTooLarge
from werkzeug.utils import secure_filename
from flask_mysqldb import MySQL, MySQLdb
from datetime import datetime
import PIL.Image as Image
import base64
import os
import io

app = Flask(__name__)

app.config['USER_NAME'] = ''
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
app.config['ALLOWED_EXTENSIONS'] = ['.jpg','.jpeg','.png']
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024;

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Shyam@2004\\mysql'
app.config['MYSQL_DB'] = 'test'

mysql = MySQL(app)

search_query = '''SELECT * FROM users WHERE user_name = %s AND user_password = %s'''
insert_query = '''INSERT INTO users VALUES (%s, %s, %s)'''

image_insert_query = '''INSERT INTO images VALUES (%s, %s, %s)'''
image_select_query = '''SELECT * FROM images WHERE user_name = %s'''

logs_insert_query = '''INSERT INTO logs VALUES (%s, %s)'''
logs_select_query = '''SELECT * FROM logs WHERE user_name = %s'''

@app.route('/', methods=['GET', 'POST'])
def home():  
    data = ''  
    return render_template('login.html', data=data)

@app.route('/home', methods=['GET', 'POST'])
def login():
    data = ''
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if isValidUser(username, password):
            app.config['USER_NAME'] = username
            load_images(app.config['USER_NAME'])
            load_log_file(app.config['USER_NAME'])

            return render_template('index.html')

        else :
            data = "Invalid Username/password entered"
            return render_template('login.html', data=data)

    return redirect(url_for('home'))

@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        msg = registerUser(username, password, email)

        if msg:
            return render_template('login.html',data='Account created successfully')

        else:
            return render_template('login.html',data='email or password are already registered')

        
    return render_template('register.html')

@app.route('/result', methods=['POST'])
def result():
    msg = ''
    try :
        file = request.files['file']
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        if(file):
            extension = os.path.splitext(filename)[1].lower()
            if extension in app.config['ALLOWED_EXTENSIONS'] :
                file.save(filepath)
                msg = 'File {} saved successfully at location {}'.format(filename, filepath)

                upload_image_to_db(filename, filepath)

            else :
                msg = 'Please select an image file'
        else:
            msg = 'Please select a file'

    except RequestEntityTooLarge:
        msg = 'uploaded image is larger than 5MB'

    with open('logs.txt', 'a') as f:
        now = datetime.now()
        log = '[{}] {}\n'.format(now, msg)
        f.write(log)

    return render_template('result.html', data = msg, image=filename)

@app.route('/gallery', methods=['GET', 'POST'])
def gallery():
    images = os.listdir(app.config['UPLOAD_FOLDER'])

    return render_template('gallery.html', images=images)

@app.route('/logs', methods = ['GET', 'POST'])
def view_logs():
    logs = list()
    with open('logs.txt', 'r') as f:
        logs.append(f.read())

    return render_template('logs.html', logs=logs)

@app.route('/logout')
def logout():
    upload_logs_file(app.config['USER_NAME'])

    images = os.listdir(app.config['UPLOAD_FOLDER'])
    for image in images:
        os.remove(os.path.join(app.config['UPLOAD_FOLDER'], image))

    with open('logs.txt', 'w') as file:
        file.write('\n')

    return render_template('login.html', data = 'Successfully logged out')

@app.route('/display-image/<filename>', methods = ['POST', 'GET'])
def display_image(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

def isValidUser(username, password):
    values = (username, password, )

    cur = mysql.connection.cursor()
    cur.execute(search_query, values)

    account_details = cur.fetchone()

    cur.close()
    if account_details:
        return True

    return False

def registerUser(username, password, email):
    values = (username, password, email, )

    try :
        cur = mysql.connection.cursor()
        cur.execute(insert_query, values)
        mysql.connection.commit()
        cur.close()
        return True

    except MySQLdb.IntegrityError:
        return False

def upload_image_to_db(filename, filepath):
    with open(filepath, 'rb') as f:
        image_bytes = base64.b64encode(f.read())

    image_name = filename
    user_name = app.config['USER_NAME']

    values = (user_name, image_name, image_bytes)

    cur = mysql.connection.cursor()

    cur.execute(image_insert_query, values)

    mysql.connection.commit()

    cur.close()

def load_images(username) :
    cur = mysql.connection.cursor()
    values = (username, )

    cur.execute(image_select_query, values)

    data = cur.fetchall()

    image_sources = list()
    image_names = list()

    for d in data:
        image_sources.append(d[2])
        image_names.append(d[1])

    i = 0

    for image in image_sources:
        image_bytes = base64.b64decode(image)
        img = Image.open(io.BytesIO(image_bytes))
        img.save(os.path.join(app.config['UPLOAD_FOLDER'],image_names[i]))
        i += 1

    cur.close()

def upload_logs_file(username):
    cur = mysql.connection.cursor()
    
    with open('logs.txt', 'rb') as file:
        logs_bytes = base64.b64encode(file.read())

    values = (username, logs_bytes, )

    cur.execute(logs_insert_query, values)

    cur.close()

def load_log_file(username):
    cur = mysql.connection.cursor()

    values = (username, )
    cur.execute(logs_select_query, values)

    data = cur.fetchone()

    if data is None:
        pass

    else:
        logs_bytes = data[1]

        logs_source = base64.b64decode(logs_bytes)

        with open('logs.txt', 'wb') as file:
            file.write(logs_source)

    cur.close()

if __name__ == '__main__' : 
    app.run(debug=True)