from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class Input(FlaskForm):
    firm = StringField('Company', validators=[DataRequired(),Length(min=2,max = 6)])

    submit = SubmitField('Enter')