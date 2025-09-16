import sys
import os

# Add the project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.auth_utils import create_user

def main():
    if len(sys.argv) != 3:
        print("Usage: python create_user.py <username> <password>")
        sys.exit(1) # Checks that exactly two arguments were passed.

    username = sys.argv[1]
    password = sys.argv[2]

    success = create_user(username, password)
    if success:
        print(f"User '{username}' created successfully.")
    else:
        print(f"Failed to create user '{username}'. It may already exist.")

if __name__ == "__main__":
    main()
