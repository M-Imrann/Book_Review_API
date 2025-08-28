from .database import SessionLocal
from .models import User
from .security import get_password_hash


def create_admin():
    """
    create admin
    """
    db = SessionLocal()

    existing_admin = db.query(User).filter(User.role == "admin").first()
    if existing_admin:
        print("Admin already exists:", existing_admin.email)
        return

    email = "admin@example.com"
    password = "admin"

    admin = User(
        email=email,
        hashed_password=get_password_hash(password),
        role="admin"
    )

    db.add(admin)
    db.commit()
    db.refresh(admin)
    print("Admin created successfully!")
    print(f"Email: {email}")
    print(f"Password: {password}")


if __name__ == "__main__":
    create_admin()
