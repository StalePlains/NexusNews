from app.py import db
from app.py import User

users = User.query.all()
for user in users:
    print(user.username)