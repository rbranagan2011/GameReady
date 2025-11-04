from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary using a key."""
    return dictionary.get(key)

@register.filter
def field_name(form, field_suffix):
    """Generate a field name for a form field."""
    return f"id_{field_suffix}"

@register.filter
def replace(value, arg):
    """Replace occurrences of a substring in a string."""
    if not value or not arg:
        return value
    
    # Split the argument by comma to get old and new values
    parts = arg.split(',')
    if len(parts) != 2:
        return value
    
    old, new = parts
    return value.replace(old, new)
