from functools import wraps

from flask import flash, g, redirect

def login_required(redirect_url="/"):
    def _login_required(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            if not g.user:
                flash("Access unauthorized.", "danger")
                return redirect(redirect_url)

            # logged in;
            retval = function(*args, **kwargs)
            return retval
        return wrapper
    return _login_required
