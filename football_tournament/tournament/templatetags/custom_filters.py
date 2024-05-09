from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def make_balls(goal_type):
    if goal_type == 'autogoal':
        filename = 'owngoal'
    else:
        filename = 'football_ball'
    html = f'<img class="goal-ball" src="/static/images/{filename}.png" alt="Ball">'
    return mark_safe(html)

@register.filter
def make_cup(n):
    html = '<img class="mvp" src="/static/images/mvp.png" alt="Cup">'
    return mark_safe(html)

@register.filter
def is_in_knockout(team, knockout_teams):
    return team in knockout_teams

@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key)