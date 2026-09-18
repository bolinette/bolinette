from enum import StrEnum


class JwtClaims(StrEnum):
    Type = "type"
    IssuedAt = "iat"
    Expires = "exp"
    Issuer = "iss"
    Audience = "aud"
    Payload = "payload"
