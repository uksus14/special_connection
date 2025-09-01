from utils import context, update_env, protected_template, protected_json
from django.http import HttpRequest, JsonResponse
from current.models import TextChange
from django.shortcuts import render

@protected_template
def profile(request: HttpRequest):
    return render(request, 'h_profile.html', context=context())

@protected_json
def rename(request: HttpRequest):
    name = f":{request.GET['name']}-"
    old_name = f":{request.user.name}-"
    for text in TextChange.objects.all():
        text.content = text.content.replace(old_name, name)
        text.save()
    request.user.env["name"] = request.GET['name']
    update_env()
    return JsonResponse({"message": "recolor successful"})

@protected_json
def recolor(request: HttpRequest):
    request.user.env["color"] = request.GET['color']
    update_env()
    return JsonResponse({"message": "recolor successful"})