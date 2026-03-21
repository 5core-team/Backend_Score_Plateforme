import secrets

def generate_random_password():
    return secrets.token_urlsafe(15)