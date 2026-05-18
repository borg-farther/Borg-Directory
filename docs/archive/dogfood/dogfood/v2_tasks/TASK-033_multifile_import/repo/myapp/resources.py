class Resource:
    def __init__(self, name, owner, public=False):
        self.name = name
        self.owner = owner  # This is a string (user name)
        self.public = public
