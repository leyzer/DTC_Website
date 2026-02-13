import sqlite3
import bcrypt

# Simulate registration
user_name = 'testuser'
full_name = 'Test User'
email = 'test@example.com'
password = 'password123'
hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

conn = sqlite3.connect('GPTLeague.db')
c = conn.cursor()
c.execute('INSERT INTO users (user_name, full_name, email, password_hash) VALUES (?, ?, ?, ?)', (user_name, full_name, email, hashed))
conn.commit()
conn.close()

# Check
conn = sqlite3.connect('GPTLeague.db')
c = conn.cursor()
users = c.execute('SELECT user_name, email FROM users').fetchall()
print('Users after simulated registration:', users)
conn.close()