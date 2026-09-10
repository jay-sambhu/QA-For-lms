import os
import tempfile
import unittest
import uuid
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from alembic.config import Config
from alembic import command

from models import User, Scan
import db


def SessionLocal():
    return db.SessionLocal()


def get_db_session():
    return db.get_db_session()


class TestAlembicMigrations(unittest.TestCase):
    """Test Alembic migration upgrade and downgrade lifecycle."""

    @classmethod
    def setUpClass(cls):
        cls.temp_file = tempfile.NamedTemporaryFile(suffix="_alembic_test.db", delete=False)
        cls.temp_file.close()
        cls.test_db_url = f"sqlite:///{cls.temp_file.name}"
        cls.alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        cls.alembic_cfg.set_main_option("sqlalchemy.url", cls.test_db_url)
        cls.engine = create_engine(cls.test_db_url, connect_args={"check_same_thread": False})

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()
        if os.path.exists(cls.temp_file.name):
            try:
                os.remove(cls.temp_file.name)
            except OSError:
                pass

    def test_alembic_upgrade_and_downgrade(self):
        """Verify upgrade to head, downgrade to base, and upgrade back to head."""
        # 1. Upgrade fresh isolated database to head
        command.upgrade(self.alembic_cfg, "head")
        with self.engine.connect() as conn:
            res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='scans'")).fetchall()
            self.assertEqual(len(res), 1)

        # 2. Downgrade to base
        command.downgrade(self.alembic_cfg, "base")
        with self.engine.connect() as conn:
            res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='scans'")).fetchall()
            self.assertEqual(len(res), 0)

        # 3. Upgrade back to head
        command.upgrade(self.alembic_cfg, "head")
        with self.engine.connect() as conn:
            res = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='scans'")).fetchall()
            self.assertEqual(len(res), 1)


class TestDatabaseUnifiedCRUD(unittest.TestCase):
    """Test unified SQLAlchemy database operations and transaction safety."""

    @classmethod
    def setUpClass(cls):
        cls.temp_file = tempfile.NamedTemporaryFile(suffix="_crud_test.db", delete=False)
        cls.temp_file.close()
        cls.test_db_url = f"sqlite:///{cls.temp_file.name}"
        cls.alembic_cfg = Config(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
        cls.alembic_cfg.set_main_option("sqlalchemy.url", cls.test_db_url)

        # Upgrade isolated database to head
        command.upgrade(cls.alembic_cfg, "head")

        cls.engine = create_engine(cls.test_db_url, connect_args={"check_same_thread": False})
        cls.session_factory = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=cls.engine))

        cls.orig_engine = db.engine
        cls.orig_session = db.SessionLocal
        cls.orig_db_url = db.db_url

        db.engine = cls.engine
        db.SessionLocal = cls.session_factory
        db.db_url = cls.test_db_url

        import api.main
        cls.orig_api_session = api.main.SessionLocal
        api.main.SessionLocal = cls.session_factory

    @classmethod
    def tearDownClass(cls):
        import api.main
        api.main.SessionLocal = cls.orig_api_session

        db.engine = cls.orig_engine
        db.SessionLocal = cls.orig_session
        db.db_url = cls.orig_db_url

        cls.session_factory.remove()
        cls.engine.dispose()
        if os.path.exists(cls.temp_file.name):
            try:
                os.remove(cls.temp_file.name)
            except OSError:
                pass

    def setUp(self):
        self.user_id = str(uuid.uuid4())
        self.scan_id = str(uuid.uuid4())

    def test_user_and_scan_relationship(self):
        """Test creating user and related scan records."""
        with SessionLocal() as db:
            user = User(
                id=self.user_id,
                email=f"test_{self.user_id[:8]}@example.com",
                role="student"
            )
            db.add(user)
            db.commit()

            scan = Scan(
                id=self.scan_id,
                user_id=self.user_id,
                url="https://example.com",
                status="pending"
            )
            db.add(scan)
            db.commit()

            # Query back
            retrieved_user = db.query(User).filter(User.id == self.user_id).first()
            self.assertIsNotNone(retrieved_user)
            self.assertEqual(len(retrieved_user.scans), 1)
            self.assertEqual(retrieved_user.scans[0].id, self.scan_id)
            self.assertEqual(retrieved_user.scans[0].status, "pending")

    def test_scan_status_lifecycle_and_paths(self):
        """Test pending -> running -> completed status updates with report paths."""
        from api.main import update_scan, get_scan

        # Create user & scan
        with SessionLocal() as db:
            user = User(id=self.user_id, email=f"life_{self.user_id[:8]}@example.com", role="student")
            db.add(user)
            scan = Scan(id=self.scan_id, user_id=self.user_id, url="https://example.com", status="pending")
            db.add(scan)
            db.commit()

        # Check pending
        s = get_scan(self.scan_id)
        self.assertEqual(s["status"], "pending")

        # Update to running
        update_scan(self.scan_id, "running")
        s = get_scan(self.scan_id)
        self.assertEqual(s["status"], "running")

        # Update to completed
        update_scan(
            self.scan_id,
            "completed",
            report_path="user_data/u1/results/final.md",
            json_path="user_data/u1/results/final.json"
        )
        s = get_scan(self.scan_id)
        self.assertEqual(s["status"], "completed")
        self.assertEqual(s["report_path"], "user_data/u1/results/final.md")
        self.assertEqual(s["json_path"], "user_data/u1/results/final.json")
        self.assertIsNotNone(s["completed_at"])

        # Update to failed
        update_scan(self.scan_id, "failed")
        s = get_scan(self.scan_id)
        self.assertEqual(s["status"], "failed")

    def test_user_isolation(self):
        """Test that user queries only return their own scans."""
        other_user_id = str(uuid.uuid4())
        other_scan_id = str(uuid.uuid4())

        with SessionLocal() as db:
            u1 = User(id=self.user_id, email=f"iso1_{self.user_id[:8]}@example.com", role="student")
            u2 = User(id=other_user_id, email=f"iso2_{other_user_id[:8]}@example.com", role="student")
            db.add_all([u1, u2])
            db.commit()

            s1 = Scan(id=self.scan_id, user_id=self.user_id, url="https://u1.com", status="pending")
            s2 = Scan(id=other_scan_id, user_id=other_user_id, url="https://u2.com", status="pending")
            db.add_all([s1, s2])
            db.commit()

            # Query scans for u1
            u1_scans = db.query(Scan).filter(Scan.user_id == self.user_id).all()
            self.assertEqual(len(u1_scans), 1)
            self.assertEqual(u1_scans[0].id, self.scan_id)

            # Query scans for u2
            u2_scans = db.query(Scan).filter(Scan.user_id == other_user_id).all()
            self.assertEqual(len(u2_scans), 1)
            self.assertEqual(u2_scans[0].id, other_scan_id)

    def test_get_db_session_transaction_rollback(self):
        """Test that get_db_session rolls back automatically on error."""
        try:
            with get_db_session() as session:
                user = User(id="invalid-user-fail", email="fail@example.com", role="student")
                session.add(user)
                # Intentionally trigger error
                raise RuntimeError("Forced transaction failure")
        except RuntimeError:
            pass

        with SessionLocal() as db:
            found = db.query(User).filter(User.id == "invalid-user-fail").first()
            self.assertIsNone(found)


if __name__ == "__main__":
    unittest.main()
