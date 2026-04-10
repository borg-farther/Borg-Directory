"""Tests for query functions - verifies N+1 problem is fixed."""
import pytest
from sqlalchemy import event
from src.models import User, Post, get_engine, get_session, Base
from src.queries import setup_db, get_users_with_posts_n_plus_1, get_shared_engine


class QueryCounter:
    """Count SQL queries executed."""
    def __init__(self):
        self.count = 0

    def reset(self):
        self.count = 0


def setup_test_db():
    """Create a fresh test database using shared engine."""
    engine = get_shared_engine()
    session = get_session(engine)

    # Clear existing data
    session.query(Post).delete()
    session.query(User).delete()
    session.commit()

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

    return engine, session


def test_query_count_n_plus_1():
    """
    Test that fetching users with posts uses at most 2 queries.
    Without joinedload/subqueryload, this will execute 1 + N queries (N+1 problem).
    """
    engine, session = setup_test_db()

    counter = QueryCounter()

    @event.listens_for(engine, "before_cursor_execute")
    def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        counter.count += 1

    result = get_users_with_posts_n_plus_1()

    # Should have at most 2 queries: one for users, one for all posts (with join)
    # Without optimization, this would be 1 + N queries
    assert counter.count <= 2, f"Expected <= 2 queries, but got {counter.count} (N+1 problem)"
    assert len(result) == 2
    assert result[0]['name'] == 'Alice'
    assert len(result[0]['posts']) == 2


def test_correctness():
    """Verify the query returns correct data."""
    result = get_users_with_posts_n_plus_1()
    assert len(result) == 2
    names = {r['name'] for r in result}
    assert names == {'Alice', 'Bob'}
