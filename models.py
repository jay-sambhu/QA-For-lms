from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, ForeignKey, Index, func
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    role = Column(String, nullable=False, server_default="user")  # 'user', 'admin'
    plan_tier = Column(String, nullable=False, server_default="free")  # 'free', 'pro', 'enterprise'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    scans = relationship("Scan", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("PaymentTransaction", back_populates="user", cascade="all, delete-orphan")


class Scan(Base):
    __tablename__ = "scans"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    url = Column(Text, nullable=False)
    status = Column(String, nullable=False, server_default="pending", index=True)
    is_authenticated = Column(Boolean, nullable=True, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    report_path = Column(Text, nullable=True)
    json_path = Column(Text, nullable=True)
    user = relationship("User", back_populates="scans")

    __table_args__ = (
        Index("ix_scans_user_created", "user_id", "created_at"),
    )


class Subscription(Base):
    __tablename__ = "subscriptions"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_id = Column(String, nullable=False)  # 'free', 'pro', 'enterprise'
    status = Column(String, nullable=False, server_default="active")  # 'active', 'past_due', 'cancelled'
    gateway = Column(String, nullable=False)  # 'stripe', 'lemonsqueezy', 'razorpay', 'paypal'
    customer_id = Column(String, nullable=True)
    subscription_id = Column(String, nullable=True, index=True)
    current_period_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="subscriptions")


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    gateway = Column(String, nullable=False)  # 'stripe', 'lemonsqueezy', 'razorpay', 'paypal'
    transaction_id = Column(String, nullable=True, index=True)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String, nullable=False, server_default="USD")
    status = Column(String, nullable=False, server_default="succeeded")  # 'succeeded', 'failed', 'pending'
    plan_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="transactions")
