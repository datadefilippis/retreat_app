from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from .user import UserResponse


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12)


class ChangePasswordResponse(BaseModel):
    message: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    message: str
    # Populated only in ENVIRONMENT=development — never in production.
    # Allows pilots to test the reset flow without an SMTP provider.
    dev_reset_url: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=12)


class ResetPasswordResponse(BaseModel):
    message: str


class VerifyEmailRequest(BaseModel):
    token: str


class VerifyEmailResponse(BaseModel):
    message: str
    # FV1 (10/9/2026, funnel): il clic sul link di verifica FA ENTRARE —
    # niente secondo login. Presenti solo alla prima verifica riuscita.
    access_token: Optional[str] = None
    token_type: str = "bearer"
    user: Optional[UserResponse] = None


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ResendVerificationResponse(BaseModel):
    message: str
