from django import template

register = template.Library()


@register.filter(name="score_to_badge")
def score_to_badge(score):
    try:
        value = float(score)
    except (TypeError, ValueError):
        return "secondary"
    if value >= 80:
        return "success"
    if value >= 60:
        return "warning"
    return "danger"


