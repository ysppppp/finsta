from flask import Flask, render_template, request, session, redirect, url_for, send_file
import os
import uuid
import hashlib
import pymysql.cursors
from functools import wraps
import time

app = Flask(__name__)
app.secret_key = "super secret key"
IMAGES_DIR = os.path.join(os.getcwd(), "images")

connection = pymysql.connect(host="localhost",
                             user="root",
                             password="",
                             db="finsta",
                             charset="utf8mb4",
                             port=3306,
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return dec

@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return render_template("index.html")

@app.route("/home")
@login_required
def home():
    return render_template("home.html", username=session["username"])

@app.route("/followmanage", methods=["GET"])
@login_required
def followmanage():
    query = "SELECT * FROM follow WHERE followeeUsername = %s AND acceptedfollow = %s"

    with connection.cursor() as cursor:
        cursor.execute(query,(session['username'], '0'))
    data = list(cursor)
    cursor.close()
    return render_template("follow.html", pending = data)

@app.route('/managefollow', methods=['GET','POST'])
def managefollow():
    if request.form:
        requestData = request.form
    print(requestData)
    followeename = session['username']
    query = "SELECT followerUsername FROM Follow WHERE followeeUsername = %s AND acceptedfollow = %s"
    with connection.cursor() as cursor:
        cursor.execute(query,(session['username'], '0'))
    data = list(cursor)
    cursor.close()
    for entries in data:
        curr_name = entries['followerUsername']
        try:
            value = requestData[str(curr_name)]
            if int(value) == 2:
                query = "DELETE FROM follow WHERE follow.followerUsername = %s AND follow.followeeUsername = %s"
                with connection.cursor() as cursor:
                    cursor.execute(query, (curr_name, session['username']))
                cursor.close()
                return redirect(url_for('/followmanage'))
            else:
                query = 'UPDATE follow SET acceptedfollow = %s WHERE follow.followerUsername = %s AND follow.followeeUsername = %s'
                with connection.cursor() as cursor:
                    cursor.execute(query, ('1', curr_name, session['username']))
                cursor.close()
                return redirect(url_for('/followmanage'))
        except:
            return redirect(url_for('home'))
    return render_template("follow.html")

@app.route("/followsomeone", methods=["POST"])
@login_required
def followsomeone():
    if request.form:
        requestData = request.form
    follower = session['username']
    followee = requestData['followee']
    if (followee == follower):
        message = "You cannot follow yourself"
        return render_template("follow.html", message=message)
    query = "SELECT * FROM follow WHERE followerUsername = %s AND followeeUsername = %s"
    with connection.cursor() as cursor:
        cursor.execute(query, (follower, followee))
    cursor.close()
    data = list(cursor)
    if(data):
        message = "you already followed this user"
        return render_template("follow.html", message = message)
    else:
        query = "INSERT INTO follow (followerUsername, followeeUsername, acceptedfollow) VALUES (%s, %s, %s);"
        with connection.cursor() as cursor:
            cursor.execute(query, (follower, followee, '0'))
        cursor.close()
        return render_template("follow.html")




@app.route("/upload", methods=["GET"])
@login_required
def upload():
    return render_template("upload.html")

@app.route("/images", methods=["GET"])
@login_required
def images():
    query = "SELECT * FROM photo WHERE photoOwner IN (SELECT followeeUsername FROM follow WHERE followerUsername=%s) ORDER BY photoID DESC"

    with connection.cursor() as cursor:
        cursor.execute(query,session['username'])
    data = list(cursor)
    return render_template("images.html", images=data)


@app.route("/image/<image_name>", methods=["GET"])
def image(image_name):
    image_location = os.path.join(IMAGES_DIR, image_name)
    if os.path.isfile(image_location):
        return send_file(image_location, mimetype="image/jpg")

@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")

@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")

@app.route("/loginAuth", methods=["POST"])
def loginAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()

        with connection.cursor() as cursor:
            query = "SELECT * FROM person WHERE username = %s AND password = %s"
            cursor.execute(query, (username, hashedPassword))
        data = cursor.fetchone()
        if data:
            session["username"] = username
            return redirect(url_for("home"))

        error = "Incorrect username or password."
        return render_template("login.html", error=error)

    error = "An unknown error has occurred. Please try again."
    return render_template("login.html", error=error)

@app.route("/registerAuth", methods=["POST"])
def registerAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()
        firstName = requestData["fname"]
        lastName = requestData["lname"]

        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO person (username, password, fname, lname) VALUES (%s, %s, %s, %s)"
                cursor.execute(query, (username, hashedPassword, firstName, lastName))
        except pymysql.err.IntegrityError:
            error = "%s is already taken." % (username)
            return render_template('register.html', error=error)

        return redirect(url_for("login"))

    error = "An error has occurred. Please try again."
    return render_template("register.html", error=error)

@app.route("/logout", methods=["GET"])
def logout():
    session.pop("username")
    return redirect("/")

@app.route("/uploadImage", methods=["POST"])
@login_required
def upload_image():
    if request.files or request.form:
        requestData = request.form
        caption = requestData["cap"]
        username = session["username"]
        taggee = requestData["tagg"]
        # print(taggee)
        image_file = request.files.get("imageToUpload", "")
        image_name = image_file.filename
        filepath = os.path.join(IMAGES_DIR, image_name)
        image_file.save(filepath)
        query = "INSERT INTO photo (timestamp, filePath, photoOwner, caption) VALUES (%s, %s, %s, %s)"
        with connection.cursor() as cursor:
            cursor.execute(query, (time.strftime('%Y-%m-%d %H:%M:%S'), image_name, username, caption))
        message = "Image has been successfully uploaded."
        cursor.close()
        query = "SELECT photoID FROM photo WHERE photoOwner = %s"
        with connection.cursor() as cursor:
            cursor.execute(query, username)
            photoID = cursor.fetchone()
        cursor.close()
        # print(photoID["photoID"])
        query = "INSERT INTO tag (username, photoID, acceptedTag) VALUES (%s, %s, %s)"
        with connection.cursor() as cursor:
            cursor.execute(query, (taggee, photoID['photoID'], "0"))
        message = "Image has been successfully uploaded."
        cursor.close()
        return render_template("upload.html", message=message)
    else:
        message = "Failed to upload image."
        return render_template("upload.html", message=message)



if __name__ == "__main__":
    if not os.path.isdir("images"):
        os.mkdir(IMAGES_DIR)
    app.run()
