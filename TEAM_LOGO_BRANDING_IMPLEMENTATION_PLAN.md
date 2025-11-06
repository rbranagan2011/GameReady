# Team Logo & Branding Implementation Plan

## Overview
Add team logo/branding capabilities to allow coaches to personalize the UI for their team. Logos can be displayed as header logos or background images, and players will see the same branding when viewing their team's data.

## Features

### 1. Logo Upload & Management
- **Location**: Team Admin section (`/team-admin/`)
- **Capabilities**:
  - Upload logo image (PNG, JPG, SVG)
  - Preview uploaded logo
  - Remove/replace logo
  - Choose display mode (header logo, background, both, or none)

### 2. Display Options
- **Header Logo**: Replace or supplement "GameReady" text in navbar
- **Background Image**: Subtle watermark/background on pages
- **Both**: Logo in header + background
- **None**: Default GameReady branding

### 3. Player Experience
- Players see the same branding when viewing their team's data
- Branding is consistent across:
  - Coach Dashboard
  - Player Dashboard
  - Schedule pages
  - Team-related pages

## Implementation Steps

### Phase 1: Database & Model Changes

#### 1.1 Add Logo Fields to Team Model
**File**: `core/models.py`

```python
# Add to Team model:
logo = models.ImageField(
    upload_to='team_logos/',
    blank=True,
    null=True,
    help_text="Team logo for branding"
)

logo_display_mode = models.CharField(
    max_length=20,
    choices=[
        ('NONE', 'No Logo'),
        ('HEADER', 'Header Logo Only'),
        ('BACKGROUND', 'Background Only'),
        ('BOTH', 'Header + Background'),
    ],
    default='NONE',
    help_text="How to display the team logo"
)

background_opacity = models.FloatField(
    default=0.05,
    validators=[MinValueValidator(0.01), MaxValueValidator(0.5)],
    help_text="Background logo opacity (0.01-0.5)"
)

background_position = models.CharField(
    max_length=20,
    choices=[
        ('CENTER', 'Center'),
        ('TOP_LEFT', 'Top Left'),
        ('TOP_RIGHT', 'Top Right'),
        ('BOTTOM_LEFT', 'Bottom Left'),
        ('BOTTOM_RIGHT', 'Bottom Right'),
    ],
    default='CENTER',
    help_text="Background logo position"
)
```

#### 1.2 Create Migration
**Command**: `python manage.py makemigrations core`
**File**: `core/migrations/0017_add_team_logo_branding.py`

```python
from django.db import migrations, models
import django.core.validators

class Migration(migrations.Migration):
    dependencies = [
        ('core', '0016_add_player_personal_label'),
    ]

    operations = [
        migrations.AddField(
            model_name='team',
            name='logo',
            field=models.ImageField(blank=True, help_text='Team logo for branding', null=True, upload_to='team_logos/'),
        ),
        migrations.AddField(
            model_name='team',
            name='logo_display_mode',
            field=models.CharField(choices=[('NONE', 'No Logo'), ('HEADER', 'Header Logo Only'), ('BACKGROUND', 'Background Only'), ('BOTH', 'Header + Background')], default='NONE', help_text='How to display the team logo', max_length=20),
        ),
        migrations.AddField(
            model_name='team',
            name='background_opacity',
            field=models.FloatField(default=0.05, help_text='Background logo opacity (0.01-0.5)', validators=[django.core.validators.MinValueValidator(0.01), django.core.validators.MaxValueValidator(0.5)]),
        ),
        migrations.AddField(
            model_name='team',
            name='background_position',
            field=models.CharField(choices=[('CENTER', 'Center'), ('TOP_LEFT', 'Top Left'), ('TOP_RIGHT', 'Top Right'), ('BOTTOM_LEFT', 'Bottom Left'), ('BOTTOM_RIGHT', 'Bottom Right')], default='CENTER', help_text='Background logo position', max_length=20),
        ),
    ]
```

### Phase 2: Forms & Validation

#### 2.1 Create Logo Upload Form
**File**: `core/forms.py`

```python
from django import forms
from .models import Team
from PIL import Image

class TeamLogoForm(forms.ModelForm):
    """Form for uploading and configuring team logo."""
    
    class Meta:
        model = Team
        fields = ['logo', 'logo_display_mode', 'background_opacity', 'background_position']
        widgets = {
            'logo': forms.FileInput(attrs={
                'accept': 'image/png,image/jpeg,image/jpg,image/svg+xml',
                'class': 'form-control'
            }),
            'logo_display_mode': forms.Select(attrs={'class': 'form-select'}),
            'background_opacity': forms.NumberInput(attrs={
                'class': 'form-control',
                'type': 'range',
                'min': '0.01',
                'max': '0.5',
                'step': '0.01'
            }),
            'background_position': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def clean_logo(self):
        """Validate uploaded logo."""
        logo = self.cleaned_data.get('logo')
        
        if logo:
            # Check file size (max 5MB)
            if logo.size > 5 * 1024 * 1024:
                raise forms.ValidationError("Logo file size must be less than 5MB.")
            
            # Check file type
            valid_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/svg+xml']
            if logo.content_type not in valid_types:
                raise forms.ValidationError("Logo must be PNG, JPG, or SVG format.")
            
            # For raster images, validate dimensions (max 2000x2000)
            if logo.content_type != 'image/svg+xml':
                try:
                    img = Image.open(logo)
                    width, height = img.size
                    if width > 2000 or height > 2000:
                        raise forms.ValidationError("Logo dimensions must be less than 2000x2000 pixels.")
                except Exception:
                    raise forms.ValidationError("Invalid image file.")
        
        return logo
```

### Phase 3: Team Admin UI Updates

#### 3.1 Update Team Admin View
**File**: `core/views.py`

```python
@login_required
def team_admin(request):
    """Team Administration for coaches - includes logo management."""
    # ... existing permission checks ...
    
    logo_form = TeamLogoForm(instance=team)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'update_logo':
            logo_form = TeamLogoForm(request.POST, request.FILES, instance=team)
            if logo_form.is_valid():
                logo_form.save()
                # No success message - smooth UI update
                return redirect('core:team_admin')
        
        elif action == 'remove_logo':
            if team.logo:
                team.logo.delete(save=False)
                team.logo = None
                team.logo_display_mode = 'NONE'
                team.save()
            return redirect('core:team_admin')
        
        # ... existing actions (rename, remove_member, delete_team) ...
    
    context = {
        'team': team,
        'name_form': name_form,
        'logo_form': logo_form,
        'coaches': coaches,
        'athletes': athletes,
        'coach_count': coach_count,
    }
    return render(request, 'core/team_admin.html', context)
```

#### 3.2 Update Team Admin Template
**File**: `templates/core/team_admin.html`

Add new section after "Share Team" card:

```html
<div class="col-md-6">
    <div class="card border-primary">
        <div class="card-header bg-primary text-white fw-semibold">
            <i class="bi bi-image"></i> Team Branding
        </div>
        <div class="card-body">
            <form method="post" enctype="multipart/form-data">
                {% csrf_token %}
                <input type="hidden" name="action" value="update_logo">
                
                <!-- Current Logo Preview -->
                {% if team.logo %}
                    <div class="mb-3 text-center">
                        <img src="{{ team.logo.url }}" alt="Team Logo" 
                             class="img-thumbnail" style="max-height: 150px; max-width: 100%;">
                        <div class="mt-2">
                            <button type="submit" name="action" value="remove_logo" 
                                    class="btn btn-sm btn-outline-danger">
                                <i class="bi bi-trash"></i> Remove Logo
                            </button>
                        </div>
                    </div>
                {% endif %}
                
                <!-- Upload Logo -->
                <div class="mb-3">
                    <label for="{{ logo_form.logo.id_for_label }}" class="form-label fw-semibold">
                        Upload Logo
                    </label>
                    {{ logo_form.logo }}
                    <small class="text-muted d-block mt-1">
                        PNG, JPG, or SVG. Max 5MB. Recommended: 200x200px or larger.
                    </small>
                </div>
                
                <!-- Display Mode -->
                <div class="mb-3">
                    <label for="{{ logo_form.logo_display_mode.id_for_label }}" class="form-label fw-semibold">
                        Display Mode
                    </label>
                    {{ logo_form.logo_display_mode }}
                    <small class="text-muted d-block mt-1">
                        Choose how the logo appears on team pages
                    </small>
                </div>
                
                <!-- Background Settings (only show if background is selected) -->
                <div id="backgroundSettings" style="display: none;">
                    <div class="mb-3">
                        <label for="{{ logo_form.background_opacity.id_for_label }}" class="form-label fw-semibold">
                            Background Opacity
                            <span id="opacityValue">({{ team.background_opacity|default:0.05 }})</span>
                        </label>
                        {{ logo_form.background_opacity }}
                    </div>
                    
                    <div class="mb-3">
                        <label for="{{ logo_form.background_position.id_for_label }}" class="form-label fw-semibold">
                            Background Position
                        </label>
                        {{ logo_form.background_position }}
                    </div>
                </div>
                
                <button type="submit" class="btn btn-primary w-100">
                    <i class="bi bi-save"></i> Save Branding Settings
                </button>
            </form>
        </div>
    </div>
</div>
```

Add JavaScript for dynamic UI:

```javascript
// Show/hide background settings based on display mode
document.addEventListener('DOMContentLoaded', function() {
    const displayMode = document.getElementById('{{ logo_form.logo_display_mode.id_for_label }}');
    const backgroundSettings = document.getElementById('backgroundSettings');
    const opacitySlider = document.getElementById('{{ logo_form.background_opacity.id_for_label }}');
    const opacityValue = document.getElementById('opacityValue');
    
    function updateBackgroundSettings() {
        const mode = displayMode.value;
        if (mode === 'BACKGROUND' || mode === 'BOTH') {
            backgroundSettings.style.display = 'block';
        } else {
            backgroundSettings.style.display = 'none';
        }
    }
    
    displayMode.addEventListener('change', updateBackgroundSettings);
    updateBackgroundSettings(); // Initial state
    
    // Update opacity display value
    if (opacitySlider) {
        opacitySlider.addEventListener('input', function() {
            opacityValue.textContent = '(' + parseFloat(this.value).toFixed(2) + ')';
        });
    }
});
```

### Phase 4: Template Integration

#### 4.1 Update Base Template
**File**: `templates/base.html`

Add logo context to context processor or view context:

```html
<!-- In navbar -->
{% if user.is_authenticated %}
    {% if user.profile.role == 'COACH' and coach_active_team.logo and coach_active_team.logo_display_mode != 'NONE' %}
        {% if coach_active_team.logo_display_mode == 'HEADER' or coach_active_team.logo_display_mode == 'BOTH' %}
            <a class="navbar-brand d-flex align-items-center" href="{% url 'core:home' %}">
                <img src="{{ coach_active_team.logo.url }}" alt="{{ coach_active_team.name }}" 
                     style="max-height: 40px; margin-right: 10px;">
                <span>GameReady</span>
            </a>
        {% else %}
            <a class="navbar-brand" href="{% url 'core:home' %}">GameReady</a>
        {% endif %}
    {% else %}
        <a class="navbar-brand" href="{% url 'core:home' %}">GameReady</a>
    {% endif %}
{% else %}
    <a class="navbar-brand" href="{% url 'core:home' %}">GameReady</a>
{% endif %}
```

Add background styling:

```html
{% block extra_css %}
<style>
    {% if user.is_authenticated %}
        {% if user.profile.role == 'COACH' and coach_active_team.logo and coach_active_team.logo_display_mode != 'NONE' %}
            {% if coach_active_team.logo_display_mode == 'BACKGROUND' or coach_active_team.logo_display_mode == 'BOTH' %}
                body {
                    background-image: url('{{ coach_active_team.logo.url }}');
                    background-repeat: no-repeat;
                    background-position: {{ coach_active_team.background_position|lower|replace:'_':' ' }};
                    background-attachment: fixed;
                    background-size: contain;
                    background-opacity: {{ coach_active_team.background_opacity }};
                }
                
                body::before {
                    content: '';
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background-image: url('{{ coach_active_team.logo.url }}');
                    background-repeat: no-repeat;
                    background-position: {{ coach_active_team.background_position|lower|replace:'_':' ' }};
                    background-attachment: fixed;
                    background-size: contain;
                    opacity: {{ coach_active_team.background_opacity }};
                    z-index: -1;
                    pointer-events: none;
                }
            {% endif %}
        {% endif %}
    {% endif %}
</style>
{% endblock %}
```

#### 4.2 Update Context Processor for Players
**File**: `core/context_processors.py`

Ensure players also get their team's logo context:

```python
def coach_active_team(request):
    """Add active team context for both coaches and athletes."""
    context = {}
    
    if request.user.is_authenticated:
        try:
            profile = request.user.profile
            
            if profile.role == Profile.Role.COACH:
                # Get active team from session or profile
                active_team_id = request.session.get('active_team_id')
                if active_team_id:
                    try:
                        active_team = Team.objects.get(id=active_team_id)
                        if active_team.members.filter(id=request.user.id).exists():
                            context['coach_active_team'] = active_team
                        else:
                            # Fallback to profile team
                            if profile.team:
                                context['coach_active_team'] = profile.team
                    except Team.DoesNotExist:
                        if profile.team:
                            context['coach_active_team'] = profile.team
                else:
                    if profile.team:
                        context['coach_active_team'] = profile.team
            
            elif profile.role == Profile.Role.ATHLETE:
                # For athletes, use their primary team (or first team if multiple)
                if profile.team:
                    context['coach_active_team'] = profile.team
                elif profile.teams.exists():
                    context['coach_active_team'] = profile.teams.first()
        
        except Profile.DoesNotExist:
            pass
    
    return context
```

### Phase 5: URL Configuration

#### 5.1 Update URLs
**File**: `GameReady/urls.py` (if not already configured)

Ensure media files are served in development:

```python
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # ... existing patterns ...
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
```

### Phase 6: Admin Panel Updates

#### 6.1 Update Django Admin
**File**: `core/admin.py`

```python
from django.contrib import admin
from .models import Team

class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'logo_display_mode', 'target_readiness']
    fields = ['name', 'target_readiness', 'join_code', 'logo', 'logo_display_mode', 
              'background_opacity', 'background_position']
    readonly_fields = ['join_code']

admin.site.register(Team, TeamAdmin)
```

## File Structure

```
core/
├── models.py (add logo fields)
├── forms.py (add TeamLogoForm)
├── views.py (update team_admin view)
├── admin.py (update TeamAdmin)
├── context_processors.py (ensure logo context)
└── migrations/
    └── 0017_add_team_logo_branding.py

templates/
├── base.html (add logo to navbar and background)
└── core/
    └── team_admin.html (add logo upload section)

media/
└── team_logos/ (created automatically by Django)
```

## Security Considerations

1. **File Upload Validation**:
   - File type validation (PNG, JPG, SVG only)
   - File size limits (max 5MB)
   - Image dimension limits (max 2000x2000 for raster)
   - Sanitize filenames

2. **Access Control**:
   - Only coaches can upload logos
   - Only coaches of the team can modify branding
   - Validate team ownership in views

3. **File Storage**:
   - Store in `media/team_logos/` directory
   - Use Django's FileField/ImageField for security
   - Consider cloud storage (S3) for production

## User Experience Enhancements

1. **Preview**:
   - Show logo preview in Team Admin
   - Live preview of display mode changes
   - Preview background opacity slider

2. **Responsive Design**:
   - Logo scales appropriately on mobile
   - Background doesn't interfere with readability
   - Header logo doesn't break navbar layout

3. **Default Behavior**:
   - If no logo uploaded, show default GameReady branding
   - Graceful fallback if logo file is missing

## Testing Checklist

- [ ] Coach can upload logo in Team Admin
- [ ] Logo appears in navbar when selected
- [ ] Background logo appears when selected
- [ ] Both modes work together
- [ ] Players see team logo on their dashboards
- [ ] Logo removal works correctly
- [ ] File validation rejects invalid files
- [ ] File size limits are enforced
- [ ] Logo displays correctly on all pages
- [ ] Responsive design works on mobile
- [ ] Background opacity slider works
- [ ] Background position changes apply correctly

## Future Enhancements

1. **Logo Variants**:
   - Light/dark mode variants
   - Favicon generation from logo

2. **Color Scheme**:
   - Extract primary color from logo
   - Apply team colors to UI elements

3. **Custom CSS**:
   - Allow coaches to add custom CSS
   - Team-specific styling

4. **Logo Templates**:
   - Provide logo templates
   - Guidelines for logo design

5. **Analytics**:
   - Track logo usage
   - A/B test branding impact

## Migration Strategy

1. **Backward Compatibility**:
   - All existing teams default to `logo_display_mode='NONE'`
   - No breaking changes to existing functionality

2. **Data Migration**:
   - No data migration needed for existing teams
   - New fields have sensible defaults

3. **Rollout**:
   - Deploy model changes first
   - Deploy UI changes second
   - Test with one team before full rollout

