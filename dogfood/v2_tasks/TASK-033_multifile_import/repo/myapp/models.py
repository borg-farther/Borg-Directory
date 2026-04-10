class User:
    def __init__(self, name, email, role="user"):
        self.name = name
        self.email = email
        self.role = role
    
    def is_admin(self):
        return self.role == "admin"
    
    def display_name(self):
        return f"{self.name} <{self.email}>"
