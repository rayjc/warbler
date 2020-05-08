"""Message model tests."""

# run these tests like:
#
#    python -m unittest test_message_model.py


import os
from datetime import datetime
from unittest import TestCase

from sqlalchemy.exc import IntegrityError

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database
os.environ['DATABASE_URL'] = "postgresql:///warbler-test"

# Now we can import app
from app import app
from models import Follows, Message, User, db

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.drop_all()
db.create_all()


class MessageModelTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        self.client = app.test_client()

        self.user1 = User(
            email="test1@test.com",
            username="testuser1",
            password="RAW_PASSWORD"
        )
        db.session.add(self.user1)
        db.session.commit()

        self.text = "testing..."
        self.user_id = self.user1.id

    def tearDown(self):
        db.session.rollback()

    def test_message_model(self):
        """Does basic model work?"""
        msg = Message(text=self.text, user_id=self.user_id)
        db.session.add(msg)
        db.session.commit()

        self.assertEqual(msg, Message.query.get(msg.id))
        self.assertEqual(self.text, Message.query.get(msg.id).text)
        self.assertEqual(self.user_id, Message.query.get(msg.id).user_id)

    def test_user_relationship(self):
        """Does basic model work?"""
        msg = Message(text=self.text, user_id=self.user_id)
        db.session.add(msg)
        db.session.commit()

        self.assertEqual(msg.user, self.user1)

    def test_null_text(self):
        with self.assertRaises(IntegrityError):
            msg = Message(user_id=self.user_id)
            db.session.add(msg)
            db.session.commit()

    def test_null_date(self):
        msg = Message(text=self.text, user_id=self.user_id)
        db.session.add(msg)
        db.session.commit()

        self.assertIsInstance(msg.timestamp, datetime)

    def test_null_user_id(self):
        with self.assertRaises(IntegrityError):
            msg = Message(text=self.text)
            db.session.add(msg)
            db.session.commit()

    def test_delete_user_cascade(self):
        msg = Message(text=self.text, user_id=self.user_id)
        db.session.add(msg)
        db.session.commit()
        msg_id = msg.id

        db.session.delete(self.user1)
        db.session.commit()

        self.assertIsNone(User.query.get(self.user_id))
        self.assertIsNone(Message.query.get(msg_id))
