from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, ForeignKey, Index, func, text
from sqlalchemy.orm import declarative_base, relationship
from uuid import uuid4

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
    api_keys = relationship("UserApiKey", back_populates="user", cascade="all, delete-orphan")


class UserApiKey(Base):
    __tablename__ = "user_api_keys"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_id = Column(String, nullable=False, server_default="gemini")  # 'gemini', 'openai', 'anthropic', 'deepseek', 'local_llm'
    key_name = Column(String, nullable=True)
    api_key = Column(Text, nullable=False)  # encrypted at rest, see api/secrets.py
    model = Column(String, nullable=True)
    endpoint = Column(String, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="api_keys")

    @property
    def secret(self):
        from api.secrets import decrypt_secret
        return decrypt_secret(self.api_key)

    def to_dict(self):
        from api.secrets import mask_secret
        from api.utils import iso_utc
        return {
            "id": self.id,
            "provider_id": self.provider_id,
            "key_name": self.key_name or f"{(self.provider_id or 'gemini').capitalize()} Key",
            "model": self.model,
            "endpoint": self.endpoint,
            "masked_key": mask_secret(self.api_key),
            "is_default": bool(self.is_default),
            "created_at": iso_utc(self.created_at),
        }


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
    trial = relationship("TrialScan", uselist=False, cascade="all, delete-orphan", passive_deletes=True)
    secret = relationship("ScanSecret", uselist=False, cascade="all, delete-orphan", passive_deletes=True)

    __table_args__ = (
        Index("ix_scans_user_created", "user_id", "created_at"),
    )


class TrialScan(Base):
    # A scan that ran on the server's AI key as one of the user's free trial scans
    __tablename__ = "trial_scans"
    scan_id = Column(String, ForeignKey("scans.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False, index=True)


class ScanSecret(Base):
    # One-off launch credentials (login password, bearer token, key pool) for
    # a queued scan: encrypted at rest, read once by the worker and deleted.
    # Keeps them out of the Celery broker / Redis dumps.
    __tablename__ = "scan_secrets"
    scan_id = Column(String, ForeignKey("scans.id", ondelete="CASCADE"), primary_key=True)
    payload = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)


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

    __table_args__ = (
        Index("ix_subscriptions_gateway_sub", "gateway", "subscription_id", unique=True),
    )


class PaymentTransaction(Base):
    __tablename__ = "payment_transactions"
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    gateway = Column(String, nullable=False)  # 'stripe', 'lemonsqueezy', 'razorpay', 'paypal'
    transaction_id = Column(String, nullable=True, index=True)
    # Gateway event id: the same delivery (retry / replay) is processed once
    event_id = Column(String, nullable=True, unique=True, index=True)
    amount_cents = Column(Integer, nullable=False)
    currency = Column(String, nullable=False, server_default="USD")
    status = Column(String, nullable=False, server_default="succeeded")  # 'succeeded', 'failed', 'pending'
    plan_id = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="transactions")


class ApiKey(Base):
    __tablename__ = "api_keys"
    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    key_value = Column(String, nullable=False, unique=True)  # encrypted at rest, see api/secrets.py
    status = Column(String, nullable=False, server_default="active")  # 'active', 'rate_limited', 'exhausted'
    service = Column(String, nullable=False, server_default="gemini")  # e.g. 'gemini'
    rate_limit_reset_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @property
    def secret(self):
        from api.secrets import decrypt_secret
        return decrypt_secret(self.key_value)


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
        from api.utils import iso_utc
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

        published = iso_utc(self.published_at)
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
            "status": self.status,
            "published_at": published,
            "created_at": iso_utc(self.created_at),
            "updated_at": iso_utc(self.updated_at),
            # camelCase aliases still read by web/src/app/blog/** and sitemap.ts
            "readingTime": self.reading_time,
            "publishedAt": published[:10] if published else "",
        }
