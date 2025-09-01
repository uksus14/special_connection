from django.utils.timesince import timesince
from datetime import datetime
from django import template
import utils

register = template.Library()

@register.filter
def timesince_short(value: datetime, since: datetime=None):
    if not value: return ""
    try:
        since = since or datetime.now()
        result = timesince(value, since).split(',')[0]
        return 'just now' if result[0] == '0' else f"{result} ago"
    except: return "timesince_short failed"

@register.filter
def to_string(value: datetime):
    if not value: return ""
    try: return utils.from_time(value)
    except: return 'to_string failed'

@register.filter
def delay(value: datetime):
    if not value: return ""
    try: return value + utils.delay
    except: return 'delay failed'
@register.filter
def undelay(value: datetime):
    if not value: return ""
    try: return value - utils.delay
    except: return 'undelay failed'

@register.filter
def stamp(value: datetime):
    if not value: return ""
    try: return value.timestamp()*1000
    except: return 'stamp failed'

@register.filter
def color_to_rgb(value: str):
    value = value.lstrip('#')
    if not value: return ""
    try: return f"{int(value[0:2], 16)},{int(value[2:4], 16)},{int(value[4:6], 16)}"
    except: return 'color_to_rgb failed'

@register.filter
def splitlines(value: str):
    if not value: return ""
    return value.split("\n")

@register.filter
def head(value: list, number: int):
    if not value: return []
    return value[:number]