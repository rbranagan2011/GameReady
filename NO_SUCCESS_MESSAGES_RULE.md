# GameReady UI/UX Rule: No Success Messages

## Rule
**Never show green success confirmation boxes or banners. The app should flow smoothly and naturally like a modern app.**

## Guidelines
- ✅ **Do**: Update the UI silently and naturally (e.g., reload page, close modals, update displays)
- ✅ **Do**: Show error messages when something goes wrong (users need to know about problems)
- ❌ **Don't**: Add `messages.success()` calls in Django views
- ❌ **Don't**: Add `showToast()` success notifications in JavaScript
- ❌ **Don't**: Display green alert banners for successful operations

## Example
**Before (bad):**
```python
messages.success(request, 'Tag added successfully!')
return redirect('core:team_schedule_settings')
```

**After (good):**
```python
# Tag added - UI will update naturally without message
return redirect('core:team_schedule_settings')
```

## When to Use This Rule
Add this rule to your prompts when working on:
- Tag management operations
- Schedule updates
- Any user actions that should feel seamless
- Any feature where success is obvious from UI changes

## Prompt Template
When you want to remind me, use this phrase:
> "Remember: No success messages - keep it smooth and modern like a native app. Errors are fine, but success should be silent and obvious from the UI."

