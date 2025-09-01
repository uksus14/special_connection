from django.http import HttpRequest, HttpResponse, HttpResponseNotAllowed, JsonResponse
from utils import to_time, protected_template, context, protected_json
from current.models import Markdown, MarkdownSlice
from special_connection.render import render_markdown
from datetime import datetime, timedelta
from django.shortcuts import render
from typing import Callable

def handle_time(func: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    def wrapper(request: HttpRequest, *args, **kwargs):
        try: time = to_time(request.GET['time'])
        except: time = datetime.now()
        for key, value in kwargs.items():
            if isinstance(value, Markdown):
                kwargs[key] = value.slice(time)
                kwargs['fallback'] = value
        args = list(args)
        for i, arg in enumerate(args):
            if isinstance(arg, Markdown):
                args[i] = arg.slice(time)        
                kwargs['fallback'] = arg
        return func(request, *args, time, **kwargs)
    return wrapper

@protected_template
@handle_time
def home(request: HttpRequest, time: datetime):
    extra = {"markdowns": Markdown.slice_all(time), "starts_existing": datetime(2025, 9, 1)}
    return render(request, 'tm_home.html', context(time)|extra)

@protected_json
def home_downtimes(request: HttpRequest): return JsonResponse({'downtimes': []})
@protected_json
def home_changes(request: HttpRequest):
    year = request.GET.get('year', None)
    month = request.GET.get('month', None)
    changes = Markdown.all_changes(year, month, False)
    changes = [{'time': change.time.timestamp()*1000, 'user': change.author.pk} for change in changes]
    return JsonResponse({'changes': changes})

@protected_json
@Markdown.handle_request
def markdown_downtimes(request: HttpRequest, markdown: Markdown):
    downtimes = markdown.downtime.history()
    downtimes = [{'start': downtime.time.timestamp()*1000,
                  'end': (downtime.end or datetime.now()).timestamp()*1000} for downtime in downtimes]
    return JsonResponse({'downtimes': downtimes})
@protected_json
@Markdown.handle_request
def markdown_changes(request: HttpRequest, markdown: Markdown):
    if request.method != 'GET': return HttpResponseNotAllowed(['GET'])
    year = request.GET.get('year', None)
    month = request.GET.get('month', None)
    changes = markdown.changes(year=year, month=month, include_downtime=False)
    changes = [{'time': change.time.timestamp()*1000, 'user': change.author.pk} for change in changes]
    return JsonResponse({'changes': changes})

@protected_template
@Markdown.handle_request
@handle_time
def markdown(request: HttpRequest, markdown: MarkdownSlice|None, time: datetime, fallback: Markdown):
    if request.method != 'GET': return HttpResponseNotAllowed(['GET'])
    if request.GET.get('render', 'false').lower() == 'true':
        if markdown is None: return HttpResponse("This markdown doesn't exist yet, if you see this message something is wrong!")
        return HttpResponse(render_markdown(markdown.text.content))
    template = 'not_yet' if markdown is None else 'tm_markdown' if markdown.active else 'deactivated'
    extra = {"starts_existing": fallback.text.first.time-timedelta(1), "markdown": markdown or fallback}
    return render(request, template+'.html', context(time)|extra)