from fastapi.security import OAuth2AuthorizationCodeBearer
from keycloak import KeycloakOpenID 
from auth.config import settings
from fastapi import Security, HTTPException, status,Depends
from pydantic import Json
from routers.schemas import UserProfile
from sqlalchemy.orm.session import Session
from database.database import get_db
from database.models import DbUser

# We are using KEYCLOAK

oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl=settings.authorization_url, 
    tokenUrl=settings.token_url, 
)

keycloak_openid = KeycloakOpenID(
    server_url=settings.server_url, 
    client_id=settings.client_id, 
    realm_name=settings.realm, 
    client_secret_key=settings.client_secret, 
    verify=True
)

async def get_idp_public_key():
    return (
        f"{keycloak_openid.public_key()}"
    )

# Get the payload/token from keycloak
async def get_payload(token: str = Security(oauth2_scheme)) -> dict:
    try:
        return keycloak_openid.decode_token(
            token,
            key= await get_idp_public_key(),
            options={
                "verify_signature": True,
                "verify_aud": False,
                "exp": True
            }
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e), # "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
# Get user infos from the payload
async def get_user_info(payload: dict = Depends(get_payload)):
    try:
        return {"Message": "OK"}
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e), # "Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    
