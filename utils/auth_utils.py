# Handles user authentication and creation using hashed passwords stored in a SQL database.
import bcrypt # hashing library used to secure passwords.
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from database.models import User
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

# Verification when user tries to log in.
def verify_user(username, password) -> bool:
    session = Session()
    try:
        user = session.query(User).filter_by(username=username).first() # finds a matching user in the users table by username.
        if user and bcrypt.checkpw(password.encode(), user.hashed_password.encode()): # checks whether the provided password matches with hashed password in database.
            return True
        return False
    except Exception as e:
        print(f"Error verifying user: {e}")
        return False
    finally:
        session.close()

def create_user(username, password):
    session = Session()
    try:
        existing = session.query(User).filter_by(username=username).first() # Checks if the user already exists. if yes, it skips to avoid duplication.
        if existing:
            print("User already exists.")
            return False
        hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode() # Encrypts the password using bcrypt wth a random salt, which makes each hash unique even if passwords are the same.
        new_user = User(username=username, hashed_password=hashed_pw)
        session.add(new_user)
        session.commit()
        print("User created.")
        return True
    except Exception as e:
        print(f"Error creating user: {e}")
        session.rollback()
        return False
    finally:
        session.close()
