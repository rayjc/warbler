"""User model tests."""

# run these tests like:
#
#    python -m unittest test_user_model.py


import os
from unittest import TestCase

from sqlalchemy.exc import IntegrityError

from app import app
from models import Follows, Message, User, db

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app


# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class UserModelTestCase(TestCase):
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
        self.user2 = User(
            email="test2@test.com",
            username="testuser2",
            password="RAW_PASSWORD"
        )
    
    def tearDown(self):
        db.session.rollback()

    def test_user_model(self):
        """Does basic model work?"""

        u = self.user1

        db.session.add(u)
        db.session.commit()

        # User should have no messages & no followers
        self.assertEqual(len(u.messages), 0)
        self.assertEqual(len(u.followers), 0)
    
    def test_repr(self):
        db.session.add(self.user1)
        db.session.commit()

        self.assertEqual(self.user1.__repr__(),
                         f"<User #{self.user1.id}: "
                         f"{self.user1.username}, {self.user1.email}>")
    
    def test_is_followed_by(self):
        db.session.add_all([self.user1, self.user2])
        db.session.commit()
        f1 = Follows(user_being_followed_id=self.user1.id,
                     user_following_id=self.user2.id)
        db.session.add(f1)
        db.session.commit()

        self.assertFalse(self.user2.is_followed_by(self.user1))
        self.assertTrue(self.user1.is_followed_by(self.user2))
    
    def test_is_following(self):
        db.session.add_all([self.user1, self.user2])
        db.session.commit()
        f1 = Follows(user_being_followed_id=self.user1.id,
                     user_following_id=self.user2.id)
        db.session.add(f1)
        db.session.commit()

        self.assertFalse(self.user1.is_following(self.user2))
        self.assertTrue(self.user2.is_following(self.user1))

    def test_sign_up(self):
        user = User.signup(
            self.user1.username, self.user1.email, self.user1.password, None
        )
        db.session.commit()

        self.assertEqual(user, User.query.get(user.id))
    
    def test_sign_up_null_username(self):
        with self.assertRaises(IntegrityError):
            user = User.signup(
                None, self.user1.email, self.user1.password, None
            )
            db.session.commit()

    def test_sign_up_null_email(self):
        with self.assertRaises(IntegrityError):
            user = User.signup(
                self.user1.username, None, self.user1.password, None
            )
            db.session.commit()

    def test_sign_up_null_password(self):
        with self.assertRaises(ValueError):
            user = User.signup(
                self.user1.username, self.user1.email, None, None
            )
            db.session.commit()

    def test_sign_up_unique_username(self):
        user = User.signup(
            self.user1.username, self.user1.email, self.user1.password, None
        )
        db.session.commit()
        with self.assertRaises(IntegrityError):
            user = User.signup(
                self.user1.username, self.user2.email, self.user2.password, None
            )
            db.session.commit()

    def test_sign_up_unique_email(self):
        user = User.signup(
            self.user1.username, self.user1.email, self.user1.password, None
        )
        db.session.commit()
        with self.assertRaises(IntegrityError):
            user = User.signup(
                self.user2.username, self.user1.email, self.user2.password, None
            )
            db.session.commit()

    def test_sign_up_default_img_urls(self):
        user = User.signup(
            self.user1.username, self.user1.email, self.user1.password, None
        )
        db.session.commit()

        self.assertEqual(user.image_url, User.image_url.default.arg)
        self.assertEqual(user.header_image_url, User.header_image_url.default.arg)

    def test_authenticate(self):
        unhashed_password = self.user1.password
        user = User.signup(
            self.user1.username, self.user1.email, self.user1.password, None
        )
        db.session.commit()
        
        self.assertEqual(
            user, User.authenticate(self.user1.username, unhashed_password)
        )

    def test_authenticate_invalid_username(self):
        unhashed_password = self.user1.password
        user = User.signup(
            self.user1.username, self.user1.email, self.user1.password, None
        )
        db.session.commit()
        
        self.assertFalse(User.authenticate("invalid_user", unhashed_password))

    def test_authenticate_invalid_password(self):
        user = User.signup(
            self.user1.username, self.user1.email, self.user1.password, None
        )
        db.session.commit()
        
        self.assertFalse(User.authenticate(self.user1.username, "some_password"))
