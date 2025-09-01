from django.http import HttpRequest, JsonResponse, HttpResponseNotAllowed, FileResponse
from utils import protected_json, protected_template, context
from django.shortcuts import render
from images.models import Image

@protected_template
def home(request: HttpRequest):
    return render(request, 'h_images.html', context()|{'images': Image.objects.filter(tmp=False)})

@protected_json
def temporary(request: HttpRequest):
    if request.method != 'POST': return HttpResponseNotAllowed(['POST'])
    file = request.FILES['image']
    img = Image.temp(author=request.user, file=file)
    return JsonResponse(img.context, status=201)

@protected_json
@Image.handle_request
def save(request: HttpRequest, image: Image):
    if request.method != 'POST': return HttpResponseNotAllowed(['POST'])
    if not image.tmp: return JsonResponse({'message': 'image is not temporary'}, status=400)
    name = request.body.decode('utf-8')
    if image.actualize(name): return JsonResponse(image.context)
    return JsonResponse({'message': 'image with that name already exists'}, status=400)

@protected_json
@Image.handle_request
def image(request: HttpRequest, image: Image):
    if request.method != 'GET': return HttpResponseNotAllowed(['GET'])
    if not image.active: return JsonResponse({'message': 'image not active'})
    return FileResponse(image.file.open())

@protected_json
@Image.handle_request
def toggle_active(request: HttpRequest, image: Image):
    if request.method != 'POST': return HttpResponseNotAllowed(['POST'])
    image.active = not image.active
    image.save()
    return JsonResponse({'message': 'image is now' + ('' if image.active else ' not') + ' active', 'status': image.active})

@protected_json
@Image.handle_request
def rename(request: HttpRequest, image: Image):
    if request.method != 'POST': return HttpResponseNotAllowed(['POST'])
    new_name: str = request.body.decode('utf-8')
    if image.rename(new_name): return JsonResponse({'message': 'rename successful'})
    return JsonResponse({'message': 'image with that name already exists'}, status=400)