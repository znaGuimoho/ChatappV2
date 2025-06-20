from config import create_app
from db import get_db
from socketio_handlers.events import register_socketio_handlers
import atexit

db, mycursor = get_db()

# Register graceful shutdown
def close_db():
    mycursor.close()
    db.close()

atexit.register(close_db)

app, socketio = create_app()

register_socketio_handlers(socketio, mycursor, db, app)
    
if __name__ == "__main__":
    socketio.run(app, debug=True, host="0.0.0.0", port=3000, allow_unsafe_werkzeug=True)
