from django.http import HttpRequest, JsonResponse, HttpResponse, HttpResponseNotAllowed
from utils import protected_template, protected_json, context
from special_connection.render import render_markdown
from django.shortcuts import render, redirect
from current.models import Markdown

@protected_template
def home(request: HttpRequest):
    return render(request, 'c_home.html', context=context()|{"markdowns": Markdown.objects.all()})

@protected_template
@Markdown.handle_request
def markdown(request: HttpRequest, markdown: Markdown):
    if request.method not in ['GET', 'POST', 'DELETE']: return HttpResponseNotAllowed(['GET', 'POST', 'DELETE'])
    if request.method == 'GET':
        if not markdown.active:
            return redirect(markdown.urlfor('tm'))
        if request.GET.get('render', 'false').lower() == 'true':
            return HttpResponse(render_markdown(markdown.text.content))
        if request.GET.get('raw', 'false').lower() == 'true':
            return HttpResponse(markdown.text.content)
        if not markdown.seen.contains(request.user): markdown.seen.add(request.user)
        return render(request, 'c_markdown.html', context()|{"markdown": markdown})
    if request.method == 'DELETE':
        markdown.delete(request.user)
        return JsonResponse({'message': 'deletion successful'})
    action = request.GET["action"]
    if action == "change-owner":
        markdown.transfer(request.user)
        return JsonResponse({'message': 'Ownership change successful'}, status=200)
    return JsonResponse({'message': 'action not recognized'}, status=403)

@protected_json
def create_md(request: HttpRequest):
    if request.method != 'PUT': return HttpResponseNotAllowed(['PUT'])
    markdown = Markdown.empty(request.GET['title'], request.user)
    return JsonResponse({"url": markdown.urlfor('e')}, status=201)