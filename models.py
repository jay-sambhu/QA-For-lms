from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, ForeignKey, Index, func
from sqlalchemy.orm import declarative_base, relationship
from uuid import uuid4

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    role = Column(String, nullable=False, server_default="user")  # 'user', 'admin'
    plan_tier = Column(String, nullable=False, server_default="free")  # 'free', 'pro', 'enterprise'
    gemini_api_key = Column(String, nullable=True)  # User's own Gemini API key for AI QA report generation
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

class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    key_value = Column(String, nullable=False, unique=True)
    status = Column(String, nullable=False, server_default="active")  # 'active', 'rate_limited', 'exhausted'
    service = Column(String, nullable=False, server_default="gemini") # e.g. 'gemini'
    rate_limit_reset_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class BlogPost(Base):
    __tablename__ = "blog_posts"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    slug = Column(String, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    excerpt = Column(Text, nullable=False)
    content = Column(Text, nullable=False)
    category = Column(String, nullable=False, server_default="AI & Automation")
    tags = Column(Text, nullable=True, server_default="")
    author_name = Column(String, nullable=False, server_default="Nexus Core Engineering")
    author_role = Column(String, nullable=False, server_default="Platform Architecture Team")
    author_avatar = Column(String, nullable=False, server_default="/logo.png")
    reading_time = Column(String, nullable=False, server_default="5 min read")
    status = Column(String, nullable=False, server_default="published", index=True)  # 'published', 'draft'
    published_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def to_dict(self):
        import json
        parsed_tags = []
        if self.tags:
            try:
                parsed_tags = json.loads(self.tags) if self.tags.strip().startswith("[") else [t.strip() for t in self.tags.split(",") if t.strip()]
            except Exception:
                parsed_tags = [t.strip() for t in self.tags.split(",") if t.strip()]

        parsed_content = []
        if self.content:
            try:
                if self.content.strip().startswith("["):
                    parsed_content = json.loads(self.content)
                else:
                    parsed_content = [p.strip() for p in self.content.split("\n\n") if p.strip()]
            except Exception:
                parsed_content = [p.strip() for p in self.content.split("\n\n") if p.strip()]

        return {
            "id": self.id,
            "slug": self.slug,
            "title": self.title,
            "excerpt": self.excerpt,
            "content": parsed_content,
            "raw_content": self.content,
            "category": self.category,
            "tags": parsed_tags,
            "author": {
                "name": self.author_name,
                "role": self.author_role,
                "avatar": self.author_avatar,
            },
            "reading_time": self.reading_time,
            "readingTime": self.reading_time,
            "status": self.status,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "publishedAt": self.published_at.strftime("%Y-%m-%d") if self.published_at else "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

