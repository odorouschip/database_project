import hashlib
import re
class password_handler:
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def compare_hashes(self, hash_1, hash_2):
        if hash_1 == hash_2:
            return True

        return False

    def valid_password(self, password):
        if len(password) < 8:
            return False
        if not re.search(r'[A-Za-z]', password):
            return False
        if not re.search(r'[0-9]', password):
            return False
        if not re.search(r'[A-Z]', password):
            return False
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False
        return True
