"""SQLAlchemy models for N+1 query demonstration."""
from sqlalchemy import Column, Integer, String, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String(100))

    posts = relationship('Post', back_populates='author')


class Post(Base):
    __tablename__ = 'posts'

    id = Column(Integer, primary_key=True)
    title = Column(String(200))
    user_id = Column(Integer, ForeignKey('users.id'))

    author = relationship('User', back_populates='posts')


def get_engine():
    return create_engine('sqlite:///:memory:')


def get_session(engine):
    Session = sessionmaker(bind=engine)
    return Session()
