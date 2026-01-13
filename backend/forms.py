# backend/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateTimeField, FileField, DecimalField, IntegerField
from wtforms.validators import DataRequired, Optional, NumberRange
from datetime import datetime, timedelta

class EventForm(FlaskForm):
    EVENT_TYPES = [
        ('workshop', 'Workshop'),
        ('competition', 'Competition'),
        ('ideathon', 'Ideathon'),
        ('seminar', 'Seminar'),
        ('hackathon', 'Hackathon'),
        ('other', 'Other')
    ]
    
    MODE_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('hybrid', 'Hybrid')
    ]
    
    title = StringField('Event Title', validators=[DataRequired()])
    description = TextAreaField('Description', validators=[DataRequired()])
    event_type = SelectField('Event Type', choices=EVENT_TYPES, validators=[DataRequired()])
    event_date = DateTimeField(
        'Event Date & Time',
        validators=[DataRequired()],
        default=datetime.now() + timedelta(days=7),
        format='%Y-%m-%dT%H:%M'
    )
    registration_deadline = DateTimeField(
        'Registration Deadline',
        validators=[DataRequired()],
        default=datetime.now() + timedelta(days=5),
        format='%Y-%m-%dT%H:%M'
    )
    mode = SelectField('Event Mode', choices=MODE_CHOICES, validators=[DataRequired()])
    venue = StringField('Venue / Meeting Link', validators=[DataRequired()])
    eligibility = TextAreaField('Eligibility Criteria (optional)', validators=[Optional()])
    poster = FileField('Event Poster (optional)')
    max_team_size = IntegerField(
        'Maximum Team Size',
        validators=[Optional(), NumberRange(min=1)],
        default=4
    )
    min_team_size = IntegerField(
        'Minimum Team Size',
        validators=[Optional(), NumberRange(min=1)],
        default=1
    )
    registration_fee = DecimalField(
        'Registration Fee (if any)',
        validators=[Optional(), NumberRange(min=0)],
        default=0.00
    )