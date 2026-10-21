from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, select
from datetime import datetime, timedelta, timezone
from typing import Optional
import logging

from app.database import get_session
from app.models import User, RevokedToken, PasswordResetToken
from app.schemas import (
    UserRegister, UserLogin, Token, UserOut,
    ForgotPasswordRequest, ForgotPasswordResponse,
    ResetPasswordRequest, MessageResponse
)
from app.security import (
    hash_password, verify_password, create_access_token,
    decode_access_token, get_token_identifier, generate_reset_token
)
from app.dependencies import get_current_user
from app.config import settings

logger = logging.getLogger("railconnect.auth")
router = APIRouter(prefix="/auth", tags=["Accounts & Authentication"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserRegister, session: Session = Depends(get_session)):
    """Register a new user account with bcrypt password hashing."""
    existing_user = session.exec(select(User).where(User.email == user_in.email.lower())).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists"
        )
    
    hashed_pwd = hash_password(user_in.password)
    user = User(
        email=user_in.email.lower(),
        full_name=user_in.full_name,
        hashed_password=hashed_pwd,
        role=user_in.role or "passenger",
        is_active=True
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login_json(credentials: UserLogin, session: Session = Depends(get_session)):
    """Authenticate with JSON payload and return a signed JWT access token."""
    user = session.exec(select(User).where(User.email == credentials.email.lower())).first()
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        email=user.email
    )


@router.post("/login/oauth", response_model=Token, include_in_schema=False)
def login_oauth_form(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    """Support standard OAuth2 form submission for FastAPI Swagger UI."""
    user = session.exec(select(User).where(User.email == form_data.username.lower())).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email, "role": user.role}
    )
    return Token(
        access_token=access_token,
        token_type="bearer",
        role=user.role,
        user_id=user.id,
        email=user.email
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    authorization: Optional[str] = Header(None),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Log out user and revoke current JWT token server-side.
    Token identifier is stored in revocation blocklist until its natural expiry.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valid Bearer token required for logout"
        )
    
    token = authorization.split(" ")[1]
    payload = decode_access_token(token)
    exp_timestamp = payload.get("exp") if payload else None
    
    if exp_timestamp:
        expires_at = datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)
    else:
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    token_id = get_token_identifier(token)
    revoked = session.exec(select(RevokedToken).where(RevokedToken.token_identifier == token_id)).first()
    if not revoked:
        revocation_entry = RevokedToken(
            token_identifier=token_id,
            expires_at=expires_at
        )
        session.add(revocation_entry)
        session.commit()
    
    return MessageResponse(message="Successfully logged out. Token has been revoked.")


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
def forgot_password(req: ForgotPasswordRequest, session: Session = Depends(get_session)):
    """
    Initiate password reset.
    Generates a cryptographically secure, time-limited, single-use token.
    Simulates email dispatch in development mode.
    """
    user = session.exec(select(User).where(User.email == req.email.lower())).first()
    if not user:
        # Standard security practice: Avoid account enumeration
        return ForgotPasswordResponse(
            message="If the email exists in our records, password reset instructions have been generated.",
            dev_reset_token=None,
            expires_in_minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
        )
    
    token = generate_reset_token()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.RESET_TOKEN_EXPIRE_MINUTES)
    
    reset_entry = PasswordResetToken(
        user_id=user.id,
        token=token,
        is_used=False,
        expires_at=expires_at
    )
    session.add(reset_entry)
    session.commit()
    
    logger.info(f"[SIMULATED EMAIL] To: {user.email} | Reset Token: {token} (Expires in {settings.RESET_TOKEN_EXPIRE_MINUTES}m)")
    
    return ForgotPasswordResponse(
        message=f"Password reset instructions generated for {user.email}.",
        dev_reset_token=token,
        expires_in_minutes=settings.RESET_TOKEN_EXPIRE_MINUTES
    )


@router.post("/reset-password", response_model=MessageResponse)
def reset_password(req: ResetPasswordRequest, session: Session = Depends(get_session)):
    """
    Reset account password using valid single-use token.
    Ensures token has not expired and has not been used previously.
    """
    reset_entry = session.exec(
        select(PasswordResetToken).where(PasswordResetToken.token == req.token)
    ).first()
    
    if not reset_entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or unrecognized password reset token"
        )
    
    if reset_entry.is_used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This password reset token has already been used"
        )
    
    # Check expiry
    now = datetime.now(timezone.utc)
    # Ensure timezone awareness for comparison
    expires_at = reset_entry.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    
    if now > expires_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset token has expired"
        )
    
    user = session.get(User, reset_entry.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated user account not found"
        )
    
    # Update password and mark token used
    user.hashed_password = hash_password(req.new_password)
    reset_entry.is_used = True
    session.add(user)
    session.add(reset_entry)
    session.commit()
    
    return MessageResponse(message="Password has been successfully updated. You may now log in with your new password.")


@router.get("/me", response_model=UserOut)
def get_profile(current_user: User = Depends(get_current_user)):
    """Retrieve profile of the currently authenticated user."""
    return current_user
