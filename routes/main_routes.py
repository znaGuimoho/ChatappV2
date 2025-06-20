from flask import session, request, redirect, url_for, render_template, send_from_directory
from werkzeug.utils import secure_filename
from flask_session import Session
import random
from string import ascii_uppercase
import os
import uuid
from datetime import datetime

def get_session_id():
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        print(f"New Session ID: {session['session_id']}")  # Debug
    return session['session_id']

def get_user_data():
    session_id = get_session_id()
    user_data = session.get(f'user_{session_id}', {})
    print(f"Get User Data - Session ID: {session_id}, User Data: {user_data}")  # Debug
    return user_data

def set_user_data(name):
    session_id = get_session_id()
    session[f'user_{session_id}'] = {'name': name}
    print(f"Set User Data - Session ID: {session_id}, Name: {name}, Session: {dict(session)}")  # Debug

def main_routes(app, mycursor, socketio, db):
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}
    upload_folder = app.config.get('UPLOAD_FOLDER')

    def allowed_file(filename):
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def generate_unique_code(length):
        while True:
            code = "".join(random.choice(ascii_uppercase) for _ in range(length * 3))
            mycursor.execute("SELECT * FROM rooms WHERE room_name = %s", (code,))
            if not mycursor.fetchone():
                break
        return code

    ### REGISTER
    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            name = request.form.get("name", "").strip()
            gmail = request.form.get("gmail", "").strip()
            password = request.form.get("passw", "").strip().upper()
            password2 = request.form.get("pass", "").strip().upper()

            print(f"Register - Name: {name}, Gmail: {gmail}, Password: {password}, Password2: {password2}")  # Debug

            if not name or not gmail or not password or not password2:
                return render_template("register.html", error="Please fill all fields.", name=name, gmail=gmail)

            if password != password2:
                return render_template("register.html", error="Passwords do not match.", name=name, gmail=gmail)

            query = "SELECT 1 FROM users WHERE gmail = %s LIMIT 1"
            mycursor.execute(query, (gmail,))
            result = mycursor.fetchone()

            if result is not None:
                return render_template("register.html", error="Email already registered.", name=name, gmail=gmail)

            mycursor.execute("INSERT INTO users (name, gmail, password) VALUES (%s, %s, %s)", (name, gmail, password))
            db.commit()
            print(f"Register - User created: {name}, Gmail: {gmail}")  # Debug
            return redirect(url_for("login"))

        return render_template("register.html")

    ### LOGIN
    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            gmail = request.form.get("gmail", "").strip()
            password = request.form.get("passw", "").strip().upper()

            print(f"Login - Gmail: {gmail}, Password: {password}")  # Debug

            query = "SELECT name FROM users WHERE gmail = %s AND password = %s LIMIT 1"
            mycursor.execute(query, (gmail, password))
            result = mycursor.fetchone()

            if result is not None:
                set_user_data(result[0])
                print(f"Login - Success: Name: {result[0]}, Session: {dict(session)}")  # Debug
                return redirect(url_for("home"))
            else:
                print(f"Login - Failed: Gmail: {gmail}")  # Debug
                return render_template("login.html", error="Email or password is incorrect.", gmail=gmail)

        print("Login - GET request")  # Debug
        return render_template("login.html")

    ### HOME
    @app.route("/home", methods=["GET", "POST"])
    def home():
        user_data = get_user_data()
        name = user_data.get('name')
        print(f"Home - Session: {dict(session)}, Name: {name}")  # Debug

        if not name:
            print("Home - No name in session, redirecting to login")  # Debug
            return redirect(url_for("login"))

        if request.method == "POST":
            code = request.form.get("code", "").strip().upper()
            join = request.form.get("join", False)
            create = request.form.get("create", False)

            print(f"Home POST - Code: {code}, Join: {join}, Create: {create}")  # Debug

            if create:
                room = generate_unique_code(4)
                mycursor.execute("INSERT INTO rooms (room_name, members) VALUES (%s, %s)", (room, 1))
                db.commit()
                print(f"Home - Created room: {room}")  # Debug
            else:
                if not code:
                    print("Home - No code provided")  # Debug
                    return render_template("temp.html", error="Please enter a room code.", name=name)
                mycursor.execute("SELECT members FROM rooms WHERE room_name = %s", (code,))
                result = mycursor.fetchone()
                if not result:
                    print(f"Home - Room not found: {code}")  # Debug
                    return render_template("temp.html", error="Room does not exist.", name=name)
                mycursor.execute("UPDATE rooms SET members = members + 1 WHERE room_name = %s", (code,))
                db.commit()
                room = code
                print(f"Home - Joining room: {room}, Updated members: {result[0] + 1}")  # Debug

            session_id = get_session_id()
            session[f'room_{session_id}'] = room
            print(f"Home - Set session room: {room}, Session: {dict(session)}")  # Debug
            return redirect(url_for("room"))

        print("Home - Rendering temp.html")  # Debug
        return render_template("temp.html", name=name)

    ### ROOM
    @app.route("/room")
    def room():
        session_id = get_session_id()
        user_data = get_user_data()
        name = user_data.get('name')
        room = session.get(f'room_{session_id}')
        print(f"Room - Session ID: {session_id}, Session: {dict(session)}, Name: {name}, Room: {room}")  # Debug

        if not room or not name:
            print("Room - Missing room or name, redirecting to home")  # Debug
            return redirect(url_for("home"))

        mycursor.execute("SELECT sender, content, timestamp FROM messages WHERE room_name = %s ORDER BY timestamp ASC", (room,))
        messages = [{"name": sender, "message": content, "timestamp": timestamp.strftime('%Y-%m-%d %H:%M:%S') if timestamp else ''} for sender, content, timestamp in mycursor.fetchall()]
        print(f"Room - Loaded {len(messages)} messages for room: {room}")  # Debug
        return render_template("room.html", code=room, messages=messages, name=name)

    ### QUIT ROOM
    @app.route("/quit_room", methods=["POST"])
    def quit_room():
        session_id = get_session_id()
        user_data = get_user_data()
        name = user_data.get('name')
        room = session.get(f'room_{session_id}')
        print(f"Quit Room - Session ID: {session_id}, Name: {name}, Room: {room}")  # Debug

        if not room or not name:
            print("Quit Room - Missing room or name, redirecting to home")  # Debug
            return redirect(url_for("home"))

        if request.form.get("quit") == "1":
            # Emit leave event via Socket.IO
            socketio.emit("leave", room=room)
            # Clear room from session
            session.pop(f'room_{session_id}', None)
            print(f"Quit Room - Cleared room from session, Session: {dict(session)}")  # Debug
            return redirect(url_for("home"))

        print("Quit Room - Invalid form data")  # Debug
        return redirect(url_for("room"))

    ### FILE UPLOAD
    @app.route('/upload', methods=['POST'])
    def upload():
        if 'file' not in request.files:
            print("Upload - No file part")  # Debug
            return "No file part", 400
        file = request.files['file']
        if file.filename == '' or not allowed_file(file.filename):
            print(f"Upload - Invalid file: {file.filename}")  # Debug
            return "Invalid file", 400

        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        print(f"Upload - Saved file: {filename} to {filepath}")  # Debug

        session_id = get_session_id()
        user_data = get_user_data()
        name = user_data.get('name')
        room = session.get(f'room_{session_id}')
        if not room or not name:
            print(f"Upload - Invalid session: Room: {room}, Name: {name}, Session ID: {session_id}")  # Debug
            return "Invalid session"

        file_url = f"/files/{filename}"
        content = {
            "name": name,
            "message": f"<a href='{file_url}' target='_blank'>📁 {filename}</a>",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        socketio.send(content, to=room)
        print(f"Upload - Sent message for file: {filename} to room: {room}")

        mycursor.execute(
            "INSERT INTO messages (room_name, sender, content, timestamp) VALUES (%s, %s, %s, %s)",
            (room, name, content['message'], datetime.now())
        )
        db.commit()
        print("Upload - Saved message to database")  # Debug

        return "", 204

    ### FILE SERVING
    @app.route('/files/<path:filename>')
    def serve_file(filename):
        print(f"Serve File - Serving: {filename}")  # Debug
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)