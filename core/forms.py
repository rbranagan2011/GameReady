from django import forms
from django.utils.safestring import mark_safe
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import ReadinessReport, TeamTag, TeamSchedule
from django.contrib.auth.models import User
from .models import Team, Profile


class StepperWidget(forms.Widget):
    """Custom stepper widget with minus (–) and plus (+) buttons for 1-10 rating"""
    
    def __init__(self, attrs=None):
        default_attrs = {
            'min': '1',
            'max': '10',
            'step': '1'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)
    
    def render(self, name, value, attrs=None, renderer=None):
        if value is None:
            value = 5
        
        final_attrs = self.build_attrs(attrs)
        widget_id = final_attrs.get('id', f'id_{name}')
        
        html = f'''
        <div class="stepper-control">
            <button type="button" class="stepper-btn stepper-minus" data-target="{widget_id}">–</button>
            <input type="text" name="{name}" value="{value}" id="{widget_id}" 
                   class="stepper-input" min="1" max="10" inputmode="numeric" pattern="[0-9]*">
            <button type="button" class="stepper-btn stepper-plus" data-target="{widget_id}">+</button>
        </div>
        '''
        return mark_safe(html)


class ReadinessReportForm(forms.ModelForm):
    """
    Athlete Check-In form for daily readiness assessment.
    """

    # All fields use custom stepper widgets for consistent 1-10 rating interface
    sleep_quality = forms.IntegerField(
        widget=StepperWidget(),
        label="Sleep quality last night?",
        initial=5
    )
    energy_fatigue = forms.IntegerField(
        widget=StepperWidget(),
        label="Energy levels today?",
        initial=5
    )
    muscle_soreness = forms.IntegerField(
        widget=StepperWidget(),
        label="Muscle soreness today?",
        initial=5
    )
    hydration = forms.IntegerField(
        widget=StepperWidget(),
        label="Hydration status right now?",
        initial=5
    )
    nutrition_quality = forms.IntegerField(
        widget=StepperWidget(),
        label="Nutrition over the past 24 hours?",
        initial=5
    )
    motivation = forms.IntegerField(
        widget=StepperWidget(),
        label="Motivation to train today?",
        initial=5
    )
    mood_stress = forms.IntegerField(
        widget=StepperWidget(),
        label="Overall headspace today?",
        initial=5
    )

    class Meta:
        model = ReadinessReport
        # User-facing fields for the readiness check-in form
        # Note: 'athlete', 'date_created', and 'readiness_score' are handled automatically
        fields = [
            'sleep_quality',
            'energy_fatigue',
            'muscle_soreness',
            'hydration',
            'nutrition_quality',
            'motivation',
            'mood_stress',
            'comments'
        ]

        widgets = {
            'comments': forms.Textarea(attrs={'rows': 4, 'class': 'form-control', 'placeholder': 'Enter any additional notes or observations...'}),
        }


class TeamScheduleForm(forms.ModelForm):
    """
    Form for coaches to set their team's weekly schedule.
    """
    
    # Define weekday choices
    WEEKDAY_CHOICES = [
        ('Mon', 'Monday'),
        ('Tue', 'Tuesday'),
        ('Wed', 'Wednesday'),
        ('Thu', 'Thursday'),
        ('Fri', 'Friday'),
        ('Sat', 'Saturday'),
        ('Sun', 'Sunday'),
    ]
    
    # Create form fields for each weekday
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Get available team tags for this schedule's team
        team = getattr(self.instance, 'team', None)
        day_tags = TeamTag.objects.filter(team=team) if team else TeamTag.objects.none()
        tag_choices = [(tag.id, tag.name) for tag in day_tags]
        
        # Create a field for each weekday
        for weekday, display in self.WEEKDAY_CHOICES:
            field_name = f'day_{weekday.lower()}'
            self.fields[field_name] = forms.ChoiceField(
                choices=tag_choices,
                label=display,
                widget=forms.Select(attrs={'class': 'form-select'})
            )
            
            # Set initial value if instance exists
            if self.instance and self.instance.weekly_schedule:
                self.fields[field_name].initial = self.instance.weekly_schedule.get(weekday)
    
    class Meta:
        model = TeamSchedule
        fields = []  # We handle all fields in __init__
    
    def clean(self):
        cleaned_data = super().clean()
        
        # Build the weekly schedule from form data
        weekly_schedule = {}
        for weekday, _ in self.WEEKDAY_CHOICES:
            field_name = f'day_{weekday.lower()}'
            if field_name in cleaned_data:
                # store tag ID (int) in JSON
                try:
                    weekly_schedule[weekday] = int(cleaned_data[field_name])
                except (TypeError, ValueError):
                    weekly_schedule[weekday] = None
        
        cleaned_data['weekly_schedule'] = weekly_schedule
        return cleaned_data
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Set the weekly schedule from cleaned data
        if 'weekly_schedule' in self.cleaned_data:
            instance.weekly_schedule = self.cleaned_data['weekly_schedule']
        
        if commit:
            instance.save()
        return instance


class TeamTagForm(forms.ModelForm):
    """
    Form for coaches to create and edit team tags.
    """
    
    class Meta:
        model = TeamTag
        fields = ['name', 'target_min', 'target_max', 'color']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Training, Match, Recovery'}),
            'target_min': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'}),
            'target_max': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '100'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
        }
        labels = {
            'name': 'Tag Name',
            'target_min': 'Minimum Target (%)',
            'target_max': 'Maximum Target (%)',
            'color': 'Color',
        }
    
    def __init__(self, *args, **kwargs):
        team = kwargs.pop('team', None)
        super().__init__(*args, **kwargs)
        
        if team:
            # Set the team for the tag
            self.instance.team = team
    
    def clean(self):
        cleaned_data = super().clean()
        target_min = cleaned_data.get('target_min')
        target_max = cleaned_data.get('target_max')
        
        if target_min is not None and target_max is not None:
            if target_min > target_max:
                raise forms.ValidationError("Minimum target cannot be greater than maximum target.")
        
        return cleaned_data


class TeamNameForm(forms.ModelForm):
    """Rename a team. Coach-only form used in Team Administration."""
    class Meta:
        model = Team
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Team name'})
        }


class AddMemberForm(forms.Form):
    """
    Attach an existing user to the coach's team and set their role.
    Assumptions:
    - We only attach existing accounts (no invitation flow yet).
    - Lookup by username or email; if both provided, username wins.
    """
    ROLE_CHOICES = [
        (Profile.Role.ATHLETE, 'Athlete'),
        (Profile.Role.COACH, 'Coach'),
    ]
    username = forms.CharField(required=False, widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    email = forms.EmailField(required=False, widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}))
    role = forms.ChoiceField(choices=ROLE_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}))

    def clean(self):
        cleaned = super().clean()
        username = cleaned.get('username')
        email = cleaned.get('email')
        if not username and not email:
            raise forms.ValidationError('Provide a username or email to add a member.')
        # Resolve user
        user = None
        if username:
            user = User.objects.filter(username=username).first()
        if not user and email:
            user = User.objects.filter(email=email).first()
        if not user:
            raise forms.ValidationError('User not found. Create the account first, then add to team.')
        cleaned['user_obj'] = user
        return cleaned


class UserSignupForm(forms.Form):
    """User registration form with password validation."""
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username', 'autofocus': True}),
        help_text='Choose a unique username'
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'})
    )
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        help_text='Your password must contain at least 8 characters.'
    )
    password2 = forms.CharField(
        label='Password confirmation',
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}),
        help_text='Enter the same password as before, for verification.'
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('A user with that username already exists.')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('A user with that email already exists.')
        return email

    def clean_password1(self):
        password1 = self.cleaned_data.get('password1')
        try:
            validate_password(password1)
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        return password1

    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('password1')
        password2 = cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("The two password fields didn't match.")
        return cleaned_data

    def save(self, role, commit=True):
        """Create User and Profile with the specified role."""
        user = User.objects.create_user(
            username=self.cleaned_data['username'],
            email=self.cleaned_data['email'],
            password=self.cleaned_data['password1']
        )
        profile = user.profile  # Created by signal
        profile.role = role
        profile.save()
        return user


class TeamCreationForm(forms.ModelForm):
    """Form for coaches to create a new team."""
    class Meta:
        model = Team
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Team name', 'autofocus': True})
        }
        labels = {
            'name': 'Team Name'
        }

    def save(self, commit=True):
        """Create team with auto-generated join_code."""
        team = super().save(commit=False)
        if commit:
            team.save()  # This will auto-generate join_code via model save()
        return team


class JoinTeamForm(forms.Form):
    """Form to join a team using a join code."""
    join_code = forms.CharField(
        max_length=8,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter team code',
            'autofocus': True,
            'style': 'text-transform: uppercase;'
        }),
        help_text='Enter the 6-character team code'
    )

    def clean_join_code(self):
        code = self.cleaned_data.get('join_code', '').upper().strip()
        if not code:
            raise forms.ValidationError('Please enter a team code.')
        try:
            team = Team.objects.get(join_code=code)
            self.cleaned_data['team'] = team
        except Team.DoesNotExist:
            raise forms.ValidationError('Invalid team code. Please check and try again.')
        return code
