#!/usr/bin/env python3
"""
Utility script to hash passwords for SynapxIA users.
Use this to generate bcrypt hashes for user registration/migration.
"""
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    return pwd_context.hash(password)


if __name__ == "__main__":
    # Example: hash the admin password
    admin_password = "Admin123!"
    hashed = hash_password(admin_password)
    print(f"Password: {admin_password}")
    print(f"Hashed:   {hashed}")
    print("\nUse this hash in your INSERT statement:")
    print(f"INSERT INTO users (username, email, password_hash, ...) VALUES")
    print(f"  ('admin', 'admin@synapxia.org', '{hashed}', ...);")
