# Team Logo Implementation Plan

## Overview
Add the ability for coaches to upload a team logo that appears naturally on both coach and player dashboards, blending seamlessly with the existing UI aesthetic.

---

## Phase 1: Backend Configuration & Model Changes

### 1.1 Django Settings (MEDIA_URL & MEDIA_ROOT)
**File**: `GameReady/settings.py`
- Add `MEDIA_ROOT = BASE_DIR / 'media'`
- Add `MEDIA_URL = '/media/'`
- Note: Media files served differently in production (use cloud storage/CDN)

### 1.2 URL Configuration for Media Files
**File**: `GameReady/urls.py`
- Add media file serving in development (only when `DEBUG=True`)
- Use `django.conf.urls.static.static()` helper
- Production will require proper web server configuration

### 1.3 Team Model Update
**File**: `core/models.py`
- Add `logo` field to `Team` model:
  - Type: `ImageField`
  - Upload path: `team_logos/%Y/%m/%d/` (organized by date)
  - Optional (`blank=True, null=True`)
  - Max size validation: Recommend 5MB limit
  - Accepted formats: JPEG, PNG, WebP (use `validate_image_file` helper)
- Consider adding `logo_thumbnail` property for optimized display
- Add image resize/optimization on save (optional but recommended)

### 1.4 Database Migration
- Create migration: `python manage.py makemigrations core`
- Run migration: `python manage.py migrate`

---

## Phase 2: Form & View Updates

### 2.1 Team Logo Form
**File**: `core/forms.py`
- Create `TeamLogoForm`:
  - Single field: `logo` (FileInput with accept="image/*")
  - Validation: File size (max 5MB), file type (JPEG/PNG/WebP)
  - Optional: Image dimensions validation (suggest max 2000x2000px)
- Update `TeamNameForm` or create combined `TeamSettingsForm` if desired

### 2.2 Team Admin View Updates
**File**: `core/views.py` - `team_admin()` function
- Handle POST with `action='upload_logo'`
- Validate coach permissions
- Process logo upload
- Optionally delete old logo file when new one is uploaded
- Flash success/error messages
- Redirect back to team_admin page

### 2.3 Logo Delete Functionality
- Add `action='delete_logo'` handler
- Remove file from filesystem
- Set `team.logo = None` and save
- Return success message

---

## Phase 3: Template Updates

### 3.1 Team Admin Page
**File**: `templates/core/team_admin.html`
- Add new card section for "Team Logo"
- Display current logo if exists (with preview)
- Upload form with file input
- "Delete logo" button (only show if logo exists)
- Use Bootstrap file input styling
- Consider image preview before upload (client-side JS)

### 3.2 Coach Dashboard
**File**: `templates/core/coach_dashboard.html`
- Add logo display in header area
- Placement options:
  1. **Preferred**: Left of "Squad Overview" title (subtle, professional)
  2. Alternative: Above date navigation (centered)
- Size: 48-64px height (responsive)
- Fallback: Show team name text if no logo
- CSS: Smooth rounded corners, subtle shadow if needed

### 3.3 Player Dashboard
**File**: `templates/core/player_dashboard.html`
- Add logo display in header/title area
- Match coach dashboard placement for consistency
- Same sizing and styling
- Consider showing only if athlete has a team

### 3.4 Base Template (Navbar) - Optional Enhancement
**File**: `templates/base.html`
- Could add small logo next to team name in user dropdown
- Keep it subtle (32px max)

---

## Phase 4: UI/UX Design Considerations

### 4.1 Logo Display Styling
```css
.team-logo {
    height: 48px;
    width: auto;
    max-width: 150px;
    object-fit: contain;
    border-radius: 8px;
    background: #fff;
    padding: 4px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}

/* Responsive */
@media (max-width: 768px) {
    .team-logo {
        height: 40px;
        max-width: 120px;
    }
}
```

### 4.2 Upload Interface
- Clean file input with Bootstrap styling
- Image preview before submission (JavaScript)
- Upload progress indicator (optional)
- Clear "Remove" option

### 4.3 Visual Integration
- Logo should feel part of the dashboard, not stuck on
- Use existing color scheme and spacing
- Maintain visual hierarchy (logo supports, doesn't dominate)
- Consider opacity/grayscale effects for subtle branding

---

## Phase 5: Security & Validation

### 5.1 File Upload Security
- Validate file extension (whitelist: .jpg, .jpeg, .png, .webp)
- Validate MIME type (server-side)
- Limit file size (5MB max)
- Sanitize filename (avoid directory traversal)
- Use Django's `ImageField` built-in validation

### 5.2 Image Processing (Optional but Recommended)
- Resize oversized images automatically
- Create thumbnail versions for performance
- Consider using `Pillow` for image manipulation
- Store optimized versions to reduce storage/bandwidth

### 5.3 Permissions
- Only coaches can upload/delete logos
- Verify coach owns the team before allowing upload
- Same permission checks as existing team_admin view

---

## Phase 6: Testing Checklist

### 6.1 Functional Testing
- [ ] Coach can upload logo via team admin
- [ ] Logo appears on coach dashboard
- [ ] Logo appears on player dashboard
- [ ] Logo deletion works correctly
- [ ] File cleanup when logo is deleted
- [ ] Error handling for invalid files
- [ ] Error handling for oversized files
- [ ] Fallback display when no logo exists

### 6.2 UI/UX Testing
- [ ] Logo integrates naturally with dashboard design
- [ ] Responsive behavior on mobile devices
- [ ] Logo doesn't break layout on small screens
- [ ] Image preview works before upload
- [ ] Visual hierarchy maintained

### 6.3 Security Testing
- [ ] Invalid file types rejected
- [ ] Oversized files rejected
- [ ] Non-coaches cannot upload logos
- [ ] File paths are secure (no directory traversal)

---

## Phase 7: Implementation Order (Recommended)

1. **Backend Setup** (Phase 1)
   - Settings, URLs, Model, Migration
   
2. **Upload Functionality** (Phase 2)
   - Form, View handlers, Basic upload
   
3. **Admin UI** (Phase 3.1)
   - Team admin page upload interface
   
4. **Display on Dashboards** (Phase 3.2 & 3.3)
   - Coach dashboard integration
   - Player dashboard integration
   
5. **Polish & Security** (Phase 4 & 5)
   - Styling refinement
   - Validation and security hardening
   
6. **Testing** (Phase 6)
   - Comprehensive testing
   - Edge case handling

---

## Technical Decisions & Assumptions

### Assumptions
- Logo upload is optional (team can exist without logo)
- Logos are team-specific (one per team)
- Only coaches can manage logos
- File storage: local filesystem in development
- Image formats: JPEG, PNG, WebP (common, browser-supported)
- Max file size: 5MB (reasonable for logos, prevents abuse)

### Dependencies
- **Required**: Django ImageField (built-in)
- **Optional but Recommended**: 
  - `Pillow` (PIL) for image processing
  - `django-imagekit` or `django-resized` for automatic thumbnails

### Storage Considerations
- **Development**: Local filesystem (simple)
- **Production**: Should use cloud storage (AWS S3, Google Cloud Storage, etc.)
  - Update `DEFAULT_FILE_STORAGE` setting
  - Use `django-storages` package
  - Not included in MVP but should be documented

---

## Files to Modify

### New Files
- None (all changes to existing files)

### Modified Files
1. `GameReady/settings.py` - MEDIA configuration
2. `GameReady/urls.py` - Media serving
3. `core/models.py` - Team.logo field
4. `core/forms.py` - TeamLogoForm
5. `core/views.py` - team_admin() updates
6. `templates/core/team_admin.html` - Upload interface
7. `templates/core/coach_dashboard.html` - Logo display
8. `templates/core/player_dashboard.html` - Logo display
9. New migration file (auto-generated)

---

## Future Enhancements (Out of Scope for MVP)

- Automatic image optimization/compression
- Multiple logo sizes (thumbnail, medium, large)
- Logo cropping/editing interface
- Logo history/versioning
- Team branding colors based on logo (auto-extract)
- Logo watermark on reports/exports

---

## Notes

- Keep logo functionality simple and focused
- Ensure backward compatibility (teams without logos)
- Maintain existing UI aesthetic and spacing
- Consider performance (image optimization)
- Document production deployment requirements

