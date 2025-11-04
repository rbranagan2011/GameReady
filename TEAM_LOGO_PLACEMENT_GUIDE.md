# Team Logo Placement & Design Guide

## Dashboard Logo Placement Options

### Option 1: Header Left (Recommended) ⭐
**Location**: Left of page title in header section
**Rationale**: Natural reading flow, professional, doesn't interfere with navigation

```
Coach Dashboard Layout:
┌─────────────────────────────────────────────────────┐
│ [Logo]  Squad Overview                              │
│          [← Date →]                                 │
│          Day Type - Training                         │
└─────────────────────────────────────────────────────┘
```

**Implementation**:
- Flexbox layout: Logo + Title side-by-side
- Logo: 48-56px height, auto width (maintain aspect ratio)
- Spacing: 12-16px gap between logo and title
- Mobile: Stack vertically or reduce logo size to 40px

**CSS Example**:
```css
.dashboard-header-with-logo {
    display: flex;
    align-items: center;
    gap: 16px;
    justify-content: center; /* or flex-start for left-align */
}

.team-logo-header {
    height: 48px;
    width: auto;
    max-width: 150px;
    object-fit: contain;
    border-radius: 6px;
    background: #fff;
    padding: 4px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}
```

---

### Option 2: Above Title (Centered)
**Location**: Centered above "Squad Overview" title
**Rationale**: More prominent, traditional logo placement

```
┌─────────────────────────────────────────────────────┐
│              [Logo]                                 │
│           Squad Overview                            │
│          [← Date →]                                 │
└─────────────────────────────────────────────────────┘
```

**Implementation**:
- Centered logo above title
- Logo: 56-64px height
- Spacing: 8px margin below logo

---

### Option 3: Date Navigation Integration
**Location**: Left side of date picker
**Rationale**: Subtle, doesn't compete with main content

```
┌─────────────────────────────────────────────────────┐
│ [Logo]  [← Date →]                                 │
│          Squad Overview                             │
└─────────────────────────────────────────────────────┘
```

---

## Visual Design Principles

### Size Guidelines
- **Desktop**: 48-56px height (proportional width)
- **Tablet**: 44-48px height
- **Mobile**: 36-40px height
- **Max Width**: 150px (prevent oversized logos)

### Styling Guidelines
```css
.team-logo {
    /* Maintain aspect ratio */
    height: 48px;
    width: auto;
    max-width: 150px;
    
    /* Smooth edges */
    border-radius: 8px;
    
    /* Subtle container */
    background: #fff;
    padding: 4px;
    
    /* Light shadow for depth */
    box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    
    /* Object fit to handle any aspect ratio */
    object-fit: contain;
    
    /* Smooth transitions */
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.team-logo:hover {
    transform: scale(1.02);
    box-shadow: 0 2px 6px rgba(0,0,0,0.15);
}
```

### Fallback (No Logo)
```html
{% if team.logo %}
    <img src="{{ team.logo.url }}" alt="{{ team.name }} logo" class="team-logo">
{% else %}
    <!-- Subtle text fallback or just team name -->
    <span class="team-name-placeholder">{{ team.name }}</span>
{% endif %}
```

---

## Player Dashboard Integration

**Same placement as coach dashboard for consistency**:
- Logo appears in same position relative to "Player Dashboard" title
- Maintains visual consistency across user roles
- Smaller size on mobile if needed

---

## Team Admin Upload Interface

### Upload Section Layout
```
┌─────────────────────────────────────────────────────┐
│ Team Logo                                           │
├─────────────────────────────────────────────────────┤
│ [Current Logo Preview - if exists]                  │
│                                                      │
│ Upload new logo:                                     │
│ [Choose File] [Upload]                               │
│                                                      │
│ [Delete Logo] (only if logo exists)                 │
│                                                      │
│ Accepted: JPEG, PNG, WebP (Max 5MB)                 │
└─────────────────────────────────────────────────────┘
```

### Upload Form Features
- Image preview before upload (JavaScript)
- File size indicator
- Clear file type requirements
- Delete button (only visible when logo exists)
- Success/error feedback

---

## Responsive Behavior

### Mobile (< 768px)
- Reduce logo size to 36-40px
- Optionally stack logo above title on very small screens
- Ensure logo doesn't push content off-screen

### Tablet (768px - 992px)
- Medium size: 44-48px
- Maintain side-by-side layout if space allows

### Desktop (> 992px)
- Full size: 48-56px
- Optimal visibility without overwhelming

---

## Accessibility

- Always include `alt` text: `alt="{{ team.name }} logo"`
- Ensure sufficient color contrast if logo contains text
- Logo should be decorative (screen readers can skip with `alt=""`)
- Keyboard navigation: Logo is not interactive, but ensure layout doesn't break focus flow

---

## Performance Considerations

- Use `object-fit: contain` to handle any aspect ratio gracefully
- Lazy loading for logos below fold (optional)
- Consider creating thumbnail versions for faster loading
- Optimize uploaded images automatically (compress/resize)

---

## Recommended Final Design (Option 1)

**Coach Dashboard Header**:
```html
<div class="header">
    <div style="display: flex; align-items: center; justify-content: center; gap: 16px; margin-bottom: 10px;">
        {% if team.logo %}
            <img src="{{ team.logo.url }}" alt="{{ team.name }} logo" 
                 class="team-logo-header">
        {% endif %}
        <div class="page-title" style="font-size:24px; font-weight:700; color:#333;">
            Squad Overview
        </div>
    </div>
    <!-- Rest of header content -->
</div>
```

**CSS**:
```css
.team-logo-header {
    height: 48px;
    width: auto;
    max-width: 150px;
    object-fit: contain;
    border-radius: 6px;
    background: #fff;
    padding: 4px;
    box-shadow: 0 1px 2px rgba(0,0,0,0.08);
}

@media (max-width: 768px) {
    .team-logo-header {
        height: 40px;
        max-width: 120px;
    }
}
```

This placement is:
- ✅ Professional and polished
- ✅ Non-intrusive
- ✅ Maintains visual hierarchy
- ✅ Works well on all screen sizes
- ✅ Consistent with modern dashboard designs

