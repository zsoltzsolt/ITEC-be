#/config.py
from pydantic import BaseModel
from internal.admin import KEYCLOAK_URL

class authConfiguration(BaseModel):
        server_url: str
        realm: str
        client_id: str
        client_secret: str
        authorization_url: str
        token_url: str

settings = authConfiguration(
    server_url=f"{KEYCLOAK_URL}",
    realm="itec",
    client_id="itec",
    client_secret="",
    authorization_url=f"{KEYCLOAK_URL}/realms/itec/protocol/openid-connect/auth",
    token_url=f"{KEYCLOAK_URL}/realms/itec/protocol/openid-connect/token",
)
