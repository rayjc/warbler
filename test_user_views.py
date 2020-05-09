"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


import os
import random
from collections import namedtuple
from unittest import TestCase

from flask import escape

from models import db, connect_db, Message, User, Follows, Likes

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


class UserViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser1 = User.signup(username="testuser1",
                                    email="test1@test.com",
                                    password="testuser",
                                    image_url=None)
        self.testuser2 = User.signup(username="testuser2",
                                    email="test2@test.com",
                                    password="testuser",
                                    image_url=None)

        db.session.commit()

    def tearDown(self):
        db.session.rollback()

    def test_routes_gated(self):
        # wrapper class for holding url and method
        Route = namedtuple("Route", ['url', 'method'])

        user_id = random.randint(1, 100)
        follow_id = random.randint(1, 100)
        routes = [
            Route(f"/users/{user_id}/following", "GET"),
            Route(f"/users/{user_id}/followers", "GET"),
            Route(f"/users/follow/{follow_id}", "POST"),
            Route(f"/users/stop-following/{follow_id}", "POST"),
            Route("/users/profile", "GET"),
            Route("/users/profile", "POST"),
            Route("/users/delete", "POST"),
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

    def test_list_users_all(self):
        with self.client as c:
            resp = c.get('/users')
            html = resp.get_data(as_text=True)

            self.assertIn(self.testuser1.username, html)
            self.assertIn(self.testuser2.username, html)

    def test_list_users_query(self):
        with self.client as c:
            resp = c.get('/users', query_string={'q': '1'})
            html = resp.get_data(as_text=True)

            self.assertIn(self.testuser1.username, html)
            self.assertNotIn(self.testuser2.username, html)

    def test_users_show(self):
        msg1 = Message(text="Message 1", user_id=self.testuser1.id)
        msg2 = Message(text="Message 2", user_id=self.testuser1.id)
        db.session.add_all([msg1, msg2])
        db.session.commit()

        with self.client as c:
            invalid_id = self.testuser1.id + self.testuser2.id
            resp = c.get(f"/users/{invalid_id}")
            self.assertEqual(resp.status_code, 404)

            resp = c.get(f"/users/{self.testuser1.id}")
            html = resp.get_data(as_text=True)
            
            self.assertEqual(resp.status_code, 200)
            self.assertIn("Message 1", html)
            self.assertIn("Message 2", html)
            self.assertIn(self.testuser1.username, html)

    def test_show_likes(self):
        msg1 = Message(text="Message 1", user_id=self.testuser1.id)
        msg2 = Message(text="Message 2", user_id=self.testuser1.id)
        db.session.add_all([msg1, msg2])
        db.session.commit()
        # user2 likes user1's message
        likes = Likes(user_id=self.testuser2.id, message_id=msg1.id)
        db.session.add(likes)
        db.session.commit()

        with self.client as c:
            invalid_id = self.testuser1.id + self.testuser2.id
            resp = c.get(f"/users/{invalid_id}/likes")
            self.assertEqual(resp.status_code, 404)
        
            resp = c.get(f"/users/{self.testuser2.id}/likes")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn("Message 1", html)
            self.assertNotIn("Message 2", html)
            self.assertIn(self.testuser1.username, html)
            self.assertIn(self.testuser2.username, html)

    def test_show_following(self):
        follow = Follows(user_being_followed_id=self.testuser2.id,
                         user_following_id=self.testuser1.id)
        db.session.add(follow)
        db.session.commit()
        invalid_id = self.testuser1.id + self.testuser2.id

        with self.client as c:
            # log in 
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser1.id

            resp = c.get(f"/users/{invalid_id}/following")
            self.assertEqual(resp.status_code, 404)

            resp = c.get(f"/users/{self.testuser1.id}/following")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(self.testuser1.username, html)
            self.assertIn(self.testuser2.username, html)

    def test_users_followers(self):
        follow = Follows(user_being_followed_id=self.testuser2.id,
                         user_following_id=self.testuser1.id)
        db.session.add(follow)
        db.session.commit()
        invalid_id = self.testuser1.id + self.testuser2.id

        with self.client as c:
            # log in 
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser1.id

            resp = c.get(f"/users/{invalid_id}/followers")
            self.assertEqual(resp.status_code, 404)

            resp = c.get(f"/users/{self.testuser2.id}/followers")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(self.testuser1.username, html)
            self.assertIn(self.testuser2.username, html)

    def test_add_follow(self):
        invalid_id = self.testuser1.id + self.testuser2.id
        with self.client as c:
            # log in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser1.id

            resp = c.post(f"/users/follow/{invalid_id}")
            self.assertEqual(resp.status_code, 404)

            resp = c.post(f"/users/follow/{self.testuser2.id}")
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location,
                             f"http://localhost/users/{self.testuser1.id}/following")
            self.assertIsNotNone(
                Follows.query.filter(
                    Follows.user_being_followed_id == self.testuser2.id,
                    Follows.user_following_id == self.testuser1.id
                ).one()
            )

    def test_stop_following(self):
        follow = Follows(user_being_followed_id=self.testuser2.id,
                         user_following_id=self.testuser1.id)
        db.session.add(follow)
        db.session.commit()

        self.assertIsNotNone(
            Follows.query.filter(
                Follows.user_being_followed_id == self.testuser2.id,
                Follows.user_following_id == self.testuser1.id
            ).one()
        )

        with self.client as c:
            # log in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser1.id

            resp = c.post(
                f"/users/stop-following/{self.testuser2.id}")
            self.assertEqual(resp.status_code, 302)
            self.assertEqual(resp.location,
                             f"http://localhost/users/{self.testuser1.id}/following")
            self.assertIsNone(
                Follows.query.filter(
                    Follows.user_being_followed_id == self.testuser2.id,
                    Follows.user_following_id == self.testuser1.id
                ).one_or_none()
            )

    def test_delete_user(self):
        user_id = self.testuser1.id
        with self.client as c:
            # log in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = user_id
        
        resp = c.post("/users/delete")
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.location,
                         f"http://localhost/signup")
        self.assertIsNone(User.query.get(user_id))

    def test_profile_render(self):
        with self.client as c:
            # log in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser1.id
            
            resp = c.get("/users/profile")
            html = resp.get_data(as_text=True)

            self.assertEqual(resp.status_code, 200)
            self.assertIn(f'value="{self.testuser1.username}"', html)
            self.assertIn(f'value="{self.testuser1.email}"', html)

    def test_profile_submit(self):
        with self.client as c:
            # log in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser1.id
            
            resp = c.post(
                "/users/profile",
                data={
                    "username": "testuser1",
                    "password": "testuser",
                    "email": "success@test.com"
                }
            )

            self.assertEqual(resp.status_code, 302)
            self.assertEqual(User.query.get(self.testuser1.id).email,
                             "success@test.com")

    def test_profile_null_username(self):
        with self.client as c:
            # log in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser1.id
            
            resp = c.post(
                "/users/profile",
                data={
                    "password": "testuser",
                    "email": "success@test.com"
                }
            )

            self.assertEqual(resp.status_code, 400)

    def test_profile_null_email(self):
        with self.client as c:
            # log in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser1.id
            
            resp = c.post(
                "/users/profile",
                data={
                    "username": "testuser1",
                    "password": "testuser",
                }
            )

            self.assertEqual(resp.status_code, 400)

    def test_profile_invalid_password(self):
        with self.client as c:
            # log in
            with c.session_transaction() as sess:
                sess[CURR_USER_KEY] = self.testuser1.id
            
            resp = c.post(
                "/users/profile",
                data={
                    "username": "testuser1",
                    "email": "success@test.com",
                    "password": "...",
                }
            )

            self.assertEqual(resp.status_code, 400)
