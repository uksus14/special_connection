from django.http import HttpRequest, HttpResponse, JsonResponse
from django.contrib.auth import get_user_model
from string import ascii_lowercase, digits
from special_connection.settings import BASE_DIR
from datetime import datetime, timedelta
from django.shortcuts import render
from json import loads, dumps
from typing import Callable
from functools import wraps
from random import choices

env: dict[str, list[dict[str, str]]]
try:
    with open("./env.json") as f:
        env = loads(f.read())
except FileNotFoundError:
    print("Set up env.json from env_example.json")
    quit()

def update_env():
    with open("./env.json", "w", encoding='utf-8') as f:
        f.write(dumps(env))
    

cyrillic = "абвгдеёжзийклмнопрстуфхцчшщъыьэюя"
ALPHABET = ascii_lowercase + ascii_lowercase.upper() + cyrillic + cyrillic.upper() + digits

def slugify(string: str) -> str:
    string = string.lower().replace(' ', '_').replace(':', '-')
    return "".join(ch for ch in string if ch in ascii_lowercase+digits+'-_')

def context(time: datetime=None):
    time = time or datetime.now()
    return {"users": env["users"], "time": time}

def get_user(pk: int):
    return get_user_model().objects.get(pk=pk)

def generate_core_id(length: int) -> str:
    return "".join(choices(ALPHABET, k=length))

def protected_factory(stopped: Callable[[HttpRequest], HttpResponse]):
    def protected(view: Callable[[HttpRequest], JsonResponse]) -> Callable[[HttpRequest], JsonResponse]:
        @wraps(view)
        def wrapper(request: HttpRequest, *args, **kwargs) -> JsonResponse:
            if request.user.is_authenticated: return view(request, *args, **kwargs)
            return stopped(request)
        return wrapper
    return protected
json_auth_fail = lambda r:JsonResponse({"message": 'user not authenticated'}, status=403)
template_auth_fail = lambda r:render(r, 'login.html', status=403)
def mixed_auth_fail(request: HttpRequest) -> HttpResponse:
    if request.method == 'GET':
        if all(request.GET.get(mod, 'false').lower() != 'true' for mod in ('raw', 'list', 'content')):
            return template_auth_fail(request)
    return json_auth_fail(request)

protected_json = protected_factory(json_auth_fail)
protected_template = protected_factory(mixed_auth_fail)

time_formatting = '%Y-%m-%d %H.%M.%S.%f'
def to_time(time: str) -> datetime:
    return datetime.strptime(time, time_formatting)
def from_time(time: datetime) -> str:
    return time.strftime(time_formatting)[:-3]

def log(line: str):
    with open(BASE_DIR / 'logs.txt', 'a', encoding='utf-8') as f:
        f.write(line+'\n')

delay = timedelta(seconds=1)