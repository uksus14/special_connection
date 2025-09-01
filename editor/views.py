from django.http import HttpRequest, JsonResponse, HttpResponse, HttpResponseNotAllowed
from utils import protected_template, context
from django.shortcuts import render, redirect
from current.models import Markdown
import json

@protected_template
def home(request: HttpRequest):
    return render(request, 'e_home.html', context=context()|{"markdowns": Markdown.objects.all()})

@protected_template
@Markdown.handle_request
def markdown(request: HttpRequest, markdown: Markdown):
    if request.method not in ['GET', 'PUT', 'POST']: return HttpResponseNotAllowed(['GET', 'PUT', 'POST'])
    if request.method == 'GET':
        if not markdown.active:
            return redirect(markdown.urlfor('tm'))
        if request.GET.get('content', 'false').lower() == 'true':
            return JsonResponse({"content": markdown.text.content})
        if not markdown.seen.contains(request.user): markdown.seen.add(request.user)
        return render(request, 'e_markdown.html', context()|{'markdown': markdown})
    if request.method == 'PUT':
        markdown.revive(request.user)
        return JsonResponse({"url": markdown.urlfor('e')})
    if request.method == 'POST':
        data = json.loads(request.body)
        content = None
        if 'title' in data:
            markdown.rename(data['title'].strip(), request.user)
        if 'content' in data:
            content = markdown.change(data['content'], request.user)
        return HttpResponse(content or "", status=200)