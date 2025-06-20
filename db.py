import mysql.connector

def get_db():
    db = mysql.connector.connect(
                host='localhost',
                user='root',
                password='Password',
                database='chatapp_v3'
    )
    mycursor = db.cursor()
    return db, mycursor