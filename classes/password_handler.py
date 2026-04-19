import hashlib

class password_handler:
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()

    def compare_hashes(self, hash_1, hash_2):
        if hash_1 == hash_2:
            return True

        return False

