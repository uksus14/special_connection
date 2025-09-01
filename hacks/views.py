from utils import context, protected_template
from django.http import HttpRequest
from django.shortcuts import render
from images.models import Image

@protected_template
def home(request: HttpRequest):
    extra = {"images": Image.objects.filter(tmp=False)[:5]}
    return render(request, 'h_home.html', context=context()|extra)