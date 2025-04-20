from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime, timedelta

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    is_subscribed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # Связи
    subscription = relationship("Subscription", back_populates="user", uselist=False)
    invite_links = relationship("InviteLink", back_populates="user")

class Subscription(Base):
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True)
    start_date = Column(DateTime, default=datetime.now)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Связи
    user = relationship("User", back_populates="subscription")

class InviteLink(Base):
    __tablename__ = 'invite_links'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    link = Column(String, unique=True, nullable=False)
    chat_id = Column(String, nullable=False)  # ID чата/канала
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.now)
    
    # Связи
    user = relationship("User", back_populates="invite_links")
