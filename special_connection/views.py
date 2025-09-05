from django.http import HttpRequest, JsonResponse, HttpResponseNotAllowed
from special_connection.render import render_markdown, setup_temp
from django.contrib.auth import authenticate, login, logout
from utils import protected_json, log, get_user
from django.shortcuts import redirect
from current.models import Markdown
from cryptography import hash
import json

def entry(request: HttpRequest):
    return redirect('c_home', permanent=True)

def login_endpoint(request: HttpRequest):
    if request.method != 'POST': return HttpResponseNotAllowed(['POST'])
    code = request.body.decode('utf-8').capitalize()
    user = authenticate(request, username=hash(code), password=code)
    if user is None: return JsonResponse({'message': 'credentials are wrong'}, status=401)
    login(request, user)
    return JsonResponse({'message': 'user authenticated'})

@protected_json
def logout_endpoint(request: HttpRequest):
    if request.method != 'POST': return HttpResponseNotAllowed(['POST'])
    logout(request)
    return JsonResponse({'message': 'logout successful'})

@protected_json
def render(request: HttpRequest):
    if request.method != 'POST': return HttpResponseNotAllowed(['POST'])
    source = setup_temp(request.body.decode())
    content = render_markdown(source)
    return JsonResponse({"content": content, "source": source})

@protected_json
def toggle(request: HttpRequest):
    if request.method != 'POST': return HttpResponseNotAllowed(['POST'])
    data = json.loads(request.body)
    id = request.GET['id']
    old = f":{data['oldName']}-{id}"
    new = f":{data['newName']}-{id}"
    count = 0
    for markdown in Markdown.objects.all():
        old_text = markdown.text.content
        if old in old_text:
            count += old_text.count(old)
            markdown.change(old_text.replace(old, new), request.user)
    log(request, f"toggling {old} to {new} {count} times")
    return JsonResponse({"message": f"successfuly replaced {count} instances of tag", "changed": bool(count)})

@protected_json
def force(request: HttpRequest):
    action = request.GET['action'].lower()
    if action == 'clear':
        from current.models import Markdown, DowntimeChange, TextChange, TitleChange, OwnershipChange
        Markdown.objects.all().delete()
        DowntimeChange.objects.all().delete()
        TextChange.objects.all().delete()
        TitleChange.objects.all().delete()
        OwnershipChange.objects.all().delete()
        return JsonResponse({'message': 'force-clear successful'})
    if action == 'switch':
        new_pk = 3-request.user.pk
        logout(request)
        login(request, get_user(new_pk))
        return JsonResponse({'message': 'force-switch successful'})