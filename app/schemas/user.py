from pydantic import BaseModel, EmailStr, ConfigDict, Field
 
 
class UserCreate(BaseModel):
    email: EmailStr
    # 72 is bcrypt's hard input limit; anything longer is not fully used.
    password: str = Field(min_length=8, max_length=72)
 
 
class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
 
    id: int
    email: EmailStr
    role: str
    is_active: bool
 
 
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
 
 
class RefreshRequest(BaseModel):
    refresh_token: str
 
 
class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str
