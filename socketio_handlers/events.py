from flask_socketio import join_room, leave_room, send
from flask import session, request
from flask_session import Session
from datetime import datetime

def register_socketio_handlers(socketio, mycursor, db, app):
    from routes.main_routes import main_routes, get_session_id, get_user_data

    main_routes(app, mycursor, socketio, db)

    @socketio.on("connect")
    def handle_connect():
        session_id = get_session_id()
        user_data = get_user_data()
        name = user_data.get("name")
        room = session.get(f"room_{session_id}")
        print(f"[DEBUG] Connect event: Session ID={session_id}, Name={name}, Room={room}, Cookies={request.cookies}")

        if not room or not name:
            print("[DEBUG] Connect aborted: no room or name in session")
            return

        join_room(room)
        content = {
            "name": "System",
            "message": f"{name} has entered the room",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        send(content, to=room)
        mycursor.execute("UPDATE rooms SET members = members + 1 WHERE room_name = %s", (room,))
        db.commit()
        print(f"[DEBUG] User {name} joined room {room}, Members updated")

    @socketio.on("disconnect")
    def handle_disconnect():
        session_id = get_session_id()
        user_data = get_user_data()
        name = user_data.get("name")
        room = session.get(f"room_{session_id}")
        print(f"[DEBUG] Disconnect event: Session ID={session_id}, Name={name}, Room={room}")

        if not room or not name:
            print("[DEBUG] Disconnect aborted: no room or name in session")
            return

        leave_room(room)
        content = {
            "name": "System",
            "message": f"{name} has left the room",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        send(content, to=room)
        mycursor.execute("UPDATE rooms SET members = members - 1 WHERE room_name = %s", (room,))
        db.commit()
        print(f"[DEBUG] User {name} left room {room}, Members updated")

    @socketio.on("leave")
    def handle_leave():
        session_id = get_session_id()
        user_data = get_user_data()
        name = user_data.get("name")
        room = session.get(f"room_{session_id}")
        print(f"[DEBUG] Leave event: Session ID={session_id}, Name={name}, Room={room}")

        if not room or not name:
            print("[DEBUG] Leave aborted: no room or name in session")
            return

        leave_room(room)
        content = {
            "name": "System",
            "message": f"{name} has left the room",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        send(content, to=room)
        mycursor.execute("UPDATE rooms SET members = members - 1 WHERE room_name = %s", (room,))
        db.commit()
        print(f"[DEBUG] User {name} left room {room}, Members updated")

    @socketio.on("message")
    def handle_message(data):
        session_id = get_session_id()
        user_data = get_user_data()
        name = user_data.get("name")
        room = session.get(f"room_{session_id}")
        message = data.get("message")
        client_room = data.get("room")

        print(f"[DEBUG] Message event: Session ID={session_id}, Name={name}, Room={room}, Client Room={client_room}, Message={message}")

        if not room or not name or not message or room != client_room:
            print(f"[DEBUG] Message aborted: Invalid data - Name={name}, Room={room}, Client Room={client_room}, Message={message}")
            return

        content = {
            "name": name,
            "message": message,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        send(content, to=room)
        mycursor.execute(
            "INSERT INTO messages (room_name, sender, content, timestamp) VALUES (%s, %s, %s, %s)",
            (room, name, message, datetime.now())
        )
        db.commit()
        print(f"[DEBUG] Message stored in DB: {message} for room {room}")

    return 1