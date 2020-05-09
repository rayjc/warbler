"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
import random
from collections import namedtuple
from unittest import TestCase

from flask import escape

from models import db, connect_db, Message, User

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler-test"


# Now we can import app

from app import app, CURR_USER_KEY

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        db.session.commit()
    
    def tearDown(self):
        db.session.rollback()

    def test_routes_gated(self):
        # wrapper class for holding url and method
        Route = namedtuple("Route", ['url', 'method'])

        message_id = random.randint(1,100)
        routes = [
            Route("/messages", "GET"),
            Route("/messages/new", "POST"),
            Route(f"/messages/{message_id}/delete", "POST"),
        ]
        with self.client as c:
            for route in routes:
                resp = {
                    "get": c.get,
                    "post": c.post,
                }[route.method.lower()](route.url)

                self.assertEqual(resp.status_code, 302,
                                 f"Failed to redirect {route}.")
                self.assertEqual(resp.location, "http://localhost/",
                                 f"Failed to redirect {route} to /.")

    def test_add_message(self):
        """Can user add a message?"""
        with self.client as c:
            # Since we need to change the session to mimic logging in,
            # we need to use the changing-session trick:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            # Now, that session setting is saved, so we can have
            # the rest of ours test

            resp = c.post("/messages/new", data={"text": "Hello"})

            # Make sure it redirects
            self.assertEqual(resp.status_code, 302)

            msg = Message.query.one()
            self.assertEqual(msg.text, "Hello")

    def test_add_message_form(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.get("/messages/new")
            html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("""<textarea class="form-control" id="text" name="text" """,
                      html)

    def test_list_message(self):
        msg1 = Message(text="Test1", user_id=self.testuser.id)
        msg2 = Message(text="Test2", user_id=self.testuser.id)
        db.session.add_all([msg1, msg2])
        db.session.commit()
        messages = Message.query.order_by(
            Message.timestamp.desc()).limit(50).all()
    
        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.get("/messages")
            html = resp.get_data(as_text=True)
            self.assertEqual(resp.status_code, 200)

            for message in messages:
                self.assertIn(message.text, html)

    def test_messages_show(self):
        msg = Message(text="Test", user_id=self.testuser.id)
        db.session.add(msg)
        db.session.commit()

        with self.client as c:

            resp = c.get(f"/messages/{msg.id}")
            html = resp.get_data(as_text=True)
            self.assertEqual(resp.status_code, 200)

        self.assertIn(msg.text, html)

    def test_messages_destroy(self):
        msg = Message(text="Test", user_id=self.testuser.id)
        db.session.add(msg)
        db.session.commit()
        msg_id = msg.id

        with self.client as c:
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser.id

            resp = c.post(f"/messages/{msg_id}/delete")

            self.assertEqual(resp.status_code, 302)
            self.assertIsNone(Message.query.get(msg_id))

