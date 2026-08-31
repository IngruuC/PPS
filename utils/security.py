
import hashlib
import secrets


def generar_salt() -> str:
    
    return secrets.token_hex(16)


def hashear_password(password: str, salt: str) -> str:
    
    hash_bytes = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000
    )
    return hash_bytes.hex()


def crear_password_hash(password: str):
   
    salt = generar_salt()
    hash_resultado = hashear_password(password, salt)
    return hash_resultado, salt


def verificar_password(password: str, hash_guardado: str, salt_guardado: str) -> bool:
    
    hash_calculado = hashear_password(password, salt_guardado)
    return secrets.compare_digest(hash_calculado, hash_guardado)