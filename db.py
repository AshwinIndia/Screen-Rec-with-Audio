import sqlite3

def check_database():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users")
    users = c.fetchall()
    for user in users:
        print(f"Username: {user[0]}, Password Hash: {user[1]}")
    conn.close()

if __name__ == "__main__":
    check_database()
