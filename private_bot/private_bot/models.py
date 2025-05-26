from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, BigInteger
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    phone = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    created_invites = relationship("Invite", back_populates="user", foreign_keys="Invite.user_id")
    received_invites = relationship("Invite", back_populates="invited_user", foreign_keys="Invite.invited_user_id")
    created_invite_links = relationship("InviteLink", back_populates="creator", foreign_keys="InviteLink.created_by_id")
    used_invite_links = relationship("InviteLink", back_populates="used_by", foreign_keys="InviteLink.used_by_id")

    @property
    def is_subscribed(self) -> bool:
        """Проверяет, есть ли у пользователя активная подписка"""
        if not self.subscriptions:
            return False
        now = datetime.now()
        active_subscription = next(
            (sub for sub in self.subscriptions if sub.is_active and sub.end_date > now),
            None
        )
        return active_subscription is not None

    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, full_name={self.full_name})>"

class Subscription(Base):
    __tablename__ = 'subscriptions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, nullable=False, default=True)
    auto_renewal = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.now)
    updated_at = Column(DateTime, nullable=False, default=datetime.now, onupdate=datetime.now)
    
    # Relationships
    user = relationship("User", back_populates="subscriptions")

    def __repr__(self):
        return f"<Subscription(id={self.id}, user_id={self.user_id}, start_date={self.start_date}, end_date={self.end_date}, is_active={self.is_active})>"

class InviteLink(Base):
    __tablename__ = 'invite_links'
    
    id = Column(Integer, primary_key=True)
    code = Column(String, unique=True, nullable=False)
    link = Column(String, unique=True, nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_used = Column(Boolean, default=False)
    used_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    used_at = Column(DateTime, nullable=True)
    
    # Relationships
    creator = relationship("User", back_populates="created_invite_links", foreign_keys=[created_by_id])
    used_by = relationship("User", back_populates="used_invite_links", foreign_keys=[used_by_id])

class Invite(Base):
    __tablename__ = 'invites'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invited_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    user = relationship("User", back_populates="created_invites", foreign_keys=[user_id])
    invited_user = relationship("User", back_populates="received_invites", foreign_keys=[invited_user_id])
