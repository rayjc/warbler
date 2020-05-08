import os

from flask import (Flask, flash, g, redirect, render_template, request,
                   session, url_for, jsonify)
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from forms import LoginForm, MessageForm, UserAddForm, UserEditForm
from models import Message, User, connect_db, db, Follows, Likes

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ.get('DATABASE_URL', 'postgres:///warbler'))

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', "it's a secret")
toolbar = DebugToolbarExtension(app)

connect_db(app)


##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """
    If we're logged in, add curr user to Flask global before making
    any request so each request has access to current user object.

    Note: g is an application global context that lasts for
        one request/response cycle unlike the session which
        remains and persists for mulitple requests/respones.
    """

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None


def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Logout user. Flash logout message."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]
        flash("Logged out!", "success")


@app.route('/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """

    form = UserAddForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                email=form.email.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()

        except IntegrityError:
            flash("Username already taken", 'danger')
            return render_template('users/signup.html', form=form)

        do_login(user)

        return redirect("/")

    else:
        return render_template('users/signup.html', form=form)


@app.route('/login', methods=["GET", "POST"])
def login():
    """Handle user login."""

    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data,
                                 form.password.data)

        if user:
            do_login(user)
            flash(f"Hello, {user.username}!", "success")
            return redirect("/")

        flash("Invalid credentials.", 'danger')

    return render_template('users/login.html', form=form)


@app.route('/logout')
def logout():
    """Handle logout of user."""

    do_logout()
    return redirect(url_for('login'))


##############################################################################
# General user routes:

@app.route('/users')
def list_users():
    """Page with listing of users.

    Can take a 'q' param in querystring to search by that username.
    """

    search = request.args.get('q')

    if not search:
        users = User.query.all()
    else:
        users = User.query.filter(User.username.like(f"%{search}%")).all()

    return render_template('users/index.html', users=users)


@app.route('/users/<int:user_id>')
def users_show(user_id):
    """Show user profile."""

    user = User.query.get_or_404(user_id)

    # snagging messages in order from the database;
    # user.messages won't be in order by default
    messages = (Message
                .query
                .filter(Message.user_id == user_id)
                .order_by(Message.timestamp.desc())
                .limit(100)
                .all())
    num_likes = len(user.likes)
    return render_template(
        'users/show.html', user=user, messages=messages, num_likes=num_likes
    )


@app.route('/users/<int:user_id>/likes')
def show_likes(user_id):
    """Show list of messages this user has liked."""

    user = User.query.get_or_404(user_id)

    # snagging messages in order from the database;
    # user.messages won't be in order by default
    messages = user.likes
    num_likes = len(user.likes)
    return render_template(
        'users/likes.html', user=user, messages=messages, num_likes=num_likes
    )


@app.route('/users/<int:user_id>/following')
def show_following(user_id):
    """Show list of people this user is following."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    num_likes = len(user.likes)
    return render_template('users/following.html', user=user, num_likes=num_likes)


@app.route('/users/<int:user_id>/followers')
def users_followers(user_id):
    """Show list of followers of this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    user = User.query.get_or_404(user_id)
    num_likes = len(user.likes)
    return render_template('users/followers.html', user=user, num_likes=num_likes)


@app.route('/users/follow/<int:follow_id>', methods=['POST'])
def add_follow(follow_id):
    """Add a follow for the currently-logged-in user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get_or_404(follow_id)
    g.user.following.append(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/stop-following/<int:follow_id>', methods=['POST'])
def stop_following(follow_id):
    """Have currently-logged-in-user stop following this user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    followed_user = User.query.get(follow_id)
    g.user.following.remove(followed_user)
    db.session.commit()

    return redirect(f"/users/{g.user.id}/following")


@app.route('/users/profile', methods=["GET", "POST"])
def profile():
    """Update profile for current user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = (
        # populate form with user object initially
        UserEditForm.new_custom_form(g.user)
        if request.method == "GET" else
        # populate form with form data
        UserEditForm(request.form)
    )

    if (form.validate_on_submit()
        and User.authenticate(g.user.username, form.password.data)):
        form.update_default(g.user) # replace empty form fields with default values
        form.populate_obj(g.user)
        try:
            db.session.commit()
        except IntegrityError:
            flash(f"Failed to update {g.user.username}", "danger")
            return redirect(url_for('homepage'))
        
        return redirect(url_for('users_show', user_id=g.user.id))

    elif (form.password.data
          and not User.authenticate(g.user.username, form.data.get('password'))):
          # render the existing form instead of redirecting
        flash(f"Failed to verify password!", "danger")
        form.password.errors.append("Incorrect password")
    
    return render_template('users/edit.html', form=form)


@app.route('/users/delete', methods=["POST"])
def delete_user():
    """Delete user."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    do_logout()

    db.session.delete(g.user)
    db.session.commit()

    return redirect("/signup")


##############################################################################
# Messages routes:

@app.route('/messages')
def list_messages():
    """
    List 50 most recent messages.
    """
    messages = Message.query.order_by(Message.timestamp.desc()).limit(50).all()

    liked_message_ids = {
        msg.id for msg in g.user.likes
    }
    user_message_ids = {
        msg.id for msg in g.user.messages
    }

    likes_msg_map = {
        like.message_id: like.id
        for like in Likes.query.filter(Likes.user_id == g.user.id)
    }

    return render_template(
        'trending.html', messages=messages,
        liked_message_ids=liked_message_ids,
        user_message_ids=user_message_ids,
        likes_msg_map=likes_msg_map,
    )


@app.route('/messages/new', methods=["GET", "POST"])
def messages_add():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    form = MessageForm()

    if form.validate_on_submit():
        msg = Message(text=form.text.data)
        g.user.messages.append(msg)
        db.session.commit()

        return redirect(f"/users/{g.user.id}")

    return render_template('messages/new.html', form=form)


@app.route('/messages/<int:message_id>', methods=["GET"])
def messages_show(message_id):
    """Show a message."""

    msg = Message.query.get(message_id)
    return render_template('messages/show.html', message=msg)


@app.route('/messages/<int:message_id>/delete', methods=["POST"])
def messages_destroy(message_id):
    """Delete a message."""

    if not g.user:
        flash("Access unauthorized.", "danger")
        return redirect("/")

    msg = Message.query.get(message_id)
    db.session.delete(msg)
    db.session.commit()

    return redirect(f"/users/{g.user.id}")


##############################################################################
# Likes REST API routes:

@app.route('/api/likes', methods=['POST'])
def create_like():
    """
    Create a like association to message based on JSON data;
    return created like in JSON.
    """
    data = request.json
    likes_data = {
        field: data.get(field)
        for field in Likes.__table__.columns.keys()
        if data.get(field)
    }
    try:
        likes = Likes(**likes_data)
        db.session.add(likes)
        db.session.commit()
    except IntegrityError as e:
        resp = jsonify({"message": e.orig.pgerror})
        return (resp, 400)
    except:
        resp = jsonify({"message": "Failed to create a like association"})
        return (resp, 400)

    resp = jsonify({"likes": likes.serialize()})
    return (resp, 201)


@app.route('/api/likes/<int:likes_id>', methods=['DELETE'])
def delete_likes(likes_id):
    """
    Remove likes association of specified id; return delete message if successful.
    """
    likes = Likes.query.get_or_404(likes_id)
    try:
        db.session.delete(likes)
        db.session.commit()
    except SQLAlchemyError:
        resp = jsonify({"message": f"Failed to delete likes({likes_id})"})
        return (resp, 400)

    return jsonify({"message": "Deleted"})


##############################################################################
# Homepage and error pages

@app.route('/')
def homepage():
    """Show homepage:

    - anon users: no messages
    - logged in: 100 most recent messages of followed_users
    """

    if g.user:
        # SELECT messages.* FROM messages
        # JOIN follows ON user_being_followed_id = messages.user_id
        # JOIN users ON users.id = user_following_id
        # WHERE users.id = 302
        following_messages = (
            Message.query
                .join(Follows, Follows.user_being_followed_id == Message.user_id)
                .join(User, User.id == Follows.user_following_id)
                .filter(User.id == g.user.id)
                # .order_by(Message.timestamp.desc())
                # .limit(100)
                # .all()
        )
        # SELECT messages.* FROM messages JOIN users WHERE user.id = messages.user_id
        user_messages = Message.query.join(User).filter(Message.user_id == g.user.id)
        # SELECT * FROM (following_messages UNION user_messages)
        # ORDER BY messages.timestamp desc
        # LIMIT 100;
        messages = (
            following_messages
                .union(user_messages)
                .order_by(Message.timestamp.desc())
                .limit(100)
                .all()
        )

        liked_message_ids = {
            msg.id for msg in g.user.likes
        }
        user_message_ids = {
            msg.id for msg in g.user.messages
        }
        likes_msg_map = {
            like.message_id: like.id
            for like in Likes.query.filter(Likes.user_id == g.user.id)
        }
        
        return render_template(
            'home.html', messages=messages,
            liked_message_ids=liked_message_ids,
            user_message_ids=user_message_ids,
            likes_msg_map=likes_msg_map,
        )

    else:
        return render_template('home-anon.html')


##############################################################################
# Turn off all caching in Flask
#   (useful for dev; in production, this kind of stuff is typically
#   handled elsewhere)
#
# https://stackoverflow.com/questions/34066804/disabling-caching-in-flask

@app.after_request
def add_header(req):
    """Add non-caching headers on every request."""

    req.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    req.headers["Pragma"] = "no-cache"
    req.headers["Expires"] = "0"
    req.headers['Cache-Control'] = 'public, max-age=0'
    return req
