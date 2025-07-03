from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_mail import MessageSchema
from sqlalchemy.orm import Session

from src.app.auth.dependencies import get_current_user, admin_required
from src.app.database import get_db
from src.app.auth.schemas import UserLogin, UserRegister, Token, UserUpdate
from src.app.models.user import User
from src.app.auth.security import hash_password, verify_password, create_access_token
import logging
from datetime import datetime, timedelta
import secrets

from src.app.services.email_service import AsyncEmailSender

router = APIRouter(tags=["Auth"])

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)




@router.post("/register", status_code=201)
async def register_user(data: UserRegister, db: Session = Depends(get_db)):

    existing = db.query(User).filter_by(email=data.email).first()

    verification_code = str(secrets.randbelow(900000) + 100000)
    verification_code_expires = datetime.utcnow() + timedelta(minutes=15)

    message = MessageSchema(
        subject="Registration was successful",
        recipients=[data.email],
        body=f"""
                    <h1>Код підтвердження</h1>
                    <p>Ваш код: <strong>{verification_code}</strong></p>
                    <p>Дійсний до: {verification_code_expires}</p>
                """,
        # subtype=MessageType.html
        subtype="html"

    )

    if existing:
        if existing.is_verified:
            raise HTTPException(status_code=400, detail="User already exists")

        if existing.verification_code_expires and existing.verification_code_expires > datetime.utcnow():
            raise HTTPException(
                status_code=400,
                detail="Verification code already sent. Check your email."
            )
        else:

            existing.verification_code = verification_code
            existing.verification_code_expires = verification_code_expires
            db.commit()

            async with AsyncEmailSender(message):
                pass
            return {"message": "New verification code sent"}



    new_user = User(
        name=data.name,
        email=data.email,
        hashed_password=hash_password(data.password),
        phone_number=data.phone_number,
        is_verified=False,
        verification_code=verification_code,
        verification_code_expires=verification_code_expires
    )

    db.add(new_user)
    db.commit()



    async with AsyncEmailSender(message):
        pass

    return {"message": "Verification code sent"}


@router.post("/verify-email")
async def verify_email(
    email: str,
    code: str,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(
        User.email == email,
        User.verification_code == code,
        User.verification_code_expires > datetime.utcnow()  # Код ще дійсний
    ).first()

    if not user:
        raise HTTPException(400, "Invalid or expired verification code")


    user.is_verified = True
    user.verification_code = None
    user.verification_code_expires = None
    db.commit()

    # return {"message": "Email successfully verified"}
    logger.info(f"User registered successfully: {user.email} (id={user.id})")
    return {"message": "User created", "user_id": user.id}



@router.post("/login", response_model=Token)
def login_user(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(email=data.email).first()

    if not user or not verify_password(data.password, user.hashed_password):
        logger.warning(f"Login failed for: {data.email}")
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user.is_verified:
        logger.warning(f"Unverified login attempt: {user.email}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email not verified. Please check your inbox."
        )

    token = create_access_token(user.id)
    logger.info(f"Login successful: {user.email} (id={user.id})")
    return {
        "access_token": token,
        "token_type": "bearer"
    }


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "phone_number": current_user.phone_number,
        "role": current_user.role
    }


@router.put("/me")
def update_user_info(
        data: UserUpdate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):

    if data.email and data.email != current_user.email:
        existing_user = db.query(User).filter(User.email == data.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exist"
            )
        current_user.email = data.email

    if data.phone_number:
        current_user.phone_number = data.phone_number

    db.commit()
    db.refresh(current_user)

    return {
        "message": "User profile updated",
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "phone_number": current_user.phone_number,
        }
    }


@router.post("/admin-only")
def admin_action(current_user: User = Depends(admin_required)):
    return {"message": f"Welcome, admin {current_user.name}"}


@router.get("/test-auth")
def test(current_user: User = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email}

