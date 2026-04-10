"""Query functions demonstrating N+1 problem."""
from src.models import User, Post, get_engine, get_session, Base


_engine = None


def get_shared_engine():
    """Get or create a shared engine for testing."""
    global _engine
    if _engine is None:
        _engine = get_engine()
        Base.metadata.create_all(_engine)
    return _engine


def setup_db():
    """Create tables and populate with sample data."""
    engine = get_shared_engine()
    session = get_session(engine)

    # Check if already seeded
    if session.query(User).count() > 0:
        return engine

    # Create users
    user1 = User(name='Alice')
    user2 = User(name='Bob')
    session.add_all([user1, user2])
    session.commit()

    # Create posts
    posts = [
        Post(title='Post 1 by Alice', user_id=user1.id),
        Post(title='Post 2 by Alice', user_id=user1.id),
        Post(title='Post 1 by Bob', user_id=user2.id),
    ]
    session.add_all(posts)
    session.commit()

    return engine


def get_users_with_posts_n_plus_1():
    """
    Fetch all users and their posts - THIS IS THE N+1 PROBLEM.
    Executes 1 query for users + N queries for each user's posts.
    """
    engine = get_shared_engine()
    session = get_session(engine)

    # First query: get all users
    users = session.query(User).all()

    result = []
    for user in users:
        # This creates a new query for each user - N+1 problem!
        posts = session.query(Post).filter(Post.user_id == user.id).all()
        result.append({'name': user.name, 'posts': [p.title for p in posts]})

    return result
