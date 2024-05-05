from django import template
from django.utils.safestring import mark_safe

register = template.Library()

@register.filter
def make_balls(value):
    html = ''.join(['<img class="goal-ball" src="/static/images/football_ball.png" alt="Ball">' for _ in range(value)])
    return mark_safe(html)

@register.filter
def make_cup(value):
    html = ''.join(['<img class="mvp" src="/static/images/mvp.png" alt="Cup">' for _ in range(value)])
    return mark_safe(html)

@register.filter
def is_in_knockout(team, knockout_teams):
    return team in knockout_teams

@register.filter(name='get_item')
def get_item(dictionary, key):
    return dictionary.get(key)