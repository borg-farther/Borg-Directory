from myapp.models import User

def can_edit(user, resource):
    """Check if user can edit a resource."""
    if user.is_admin():
        return True
    # BUG: checks resource.owner == user instead of resource.owner == user.name
    return resource.owner == user
    
def can_delete(user, resource):
    """Only admins and owners can delete."""
    if user.is_admin():
        return True
    # Same bug
    return resource.owner == user

def can_view(user, resource):
    """Anyone can view public resources, only owner/admin for private."""
    if resource.public:
        return True
    if user.is_admin():
        return True
    return resource.owner == user  # Same bug
