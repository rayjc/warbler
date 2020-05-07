from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField, TextAreaField
from wtforms.validators import URL, DataRequired, Email, Length, Optional

from models import DEFAULT_HEADER_IMG, DEFAULT_IMG


class MessageForm(FlaskForm):
    """Form for adding/editing messages."""

    text = TextAreaField('text', validators=[DataRequired()])


class UserAddForm(FlaskForm):
    """Form for adding users."""

    username = StringField('Username', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    image_url = StringField('(Optional) Image URL', validators=[URL()])


class UserEditForm(FlaskForm):
    """Form for editing users."""

    username = StringField('Username', validators=[DataRequired()])
    email = StringField('E-mail', validators=[DataRequired(), Email()])
    image_url = StringField('(Optional) Image URL', validators=[Optional(), URL()])
    header_image_url = StringField('(Optional) Background Image URL', validators=[Optional(), URL()])
    location = StringField('Location')
    bio = TextAreaField(
        'Bio',
        validators=[Length(max=1000, message="Sorry, your bio must be under 1000 characters.")],
        render_kw={"rows": 5}
    )
    password = PasswordField('Verify Password', validators=[DataRequired(), Length(min=6)])

    @classmethod
    def new_custom_form(cls, user):
        """
        Create and populate a form based on user; return a new form
        with empty password field and empty image url fields if default
        static images are used by the user.
        """
        new_form = cls(obj=user)
        if new_form.image_url.data == DEFAULT_IMG:
            new_form.image_url.data = None
        if new_form.header_image_url.data == DEFAULT_HEADER_IMG:
            new_form.header_image_url.data = None
        new_form.password.data = None
        return new_form

    def update_default(self, user):
        """
        Update empty form url data to be default static urls;
        prevent user from updating password.
        """
        if not self.image_url.data:
            self.image_url.data = DEFAULT_IMG
        if not self.header_image_url.data:
            self.header_image_url.data = DEFAULT_HEADER_IMG
        # override submitted password with password stored on db to prevent update
        self.password.data = user.password


class LoginForm(FlaskForm):
    """Login form."""

    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
