from django.http import HttpRequest, HttpResponse, JsonResponse
from current.models import User, TextChange
from datetime import datetime, timedelta
from typing import Self, Callable
from django.urls import reverse
from django.db import models
from string import hexdigits
from random import choices

class Image(models.Model):
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    name = models.CharField(max_length=100, unique=True)
    active = models.BooleanField(blank=True, default=True)
    tmp = models.BooleanField(blank=True, default=True)
    created_at = models.DateTimeField(blank=True, auto_now_add=True)
    file = models.FileField()
    
    class Meta: ordering = ['-created_at']
    @property
    def url(self): return reverse('image', kwargs={'name': self.name})
    @property
    def wrap(self): return f"!image({self.name})"
    @property
    def context(self): return {'url': self.url, 'wrap': self.wrap}
    @classmethod
    def temp(cls, author: User, file: models.FileField) -> Self:
        cutoff = datetime.now() - timedelta(days=1)
        cls.objects.filter(tmp=True, created_at__lt=cutoff).delete()
        return cls.objects.create(author=author, name="".join(choices(hexdigits, k=10)), file=file)
    def actualize(self, name: str=None):
        if name:
            if self.get(name): return False
            self.name = name
        self.tmp = False
        self.created_at = datetime.now()
        self.save()
        return True
    @classmethod
    def handle_request(cls, func: Callable[[HttpRequest, Self], HttpResponse]) -> Callable[[HttpRequest, int, str], HttpResponse]:
        def view(request: HttpRequest, name: str, *args, **kwargs) -> HttpResponse:
            img = cls.get(name)
            if img is None: return JsonResponse({'message': f'image {name} does not exist'}, status=404)
            return func(request, img, *args, **kwargs)
        return view
    @classmethod
    def get(cls, name: str) -> Self|None:
        try: return cls.objects.get(name=name)
        except cls.DoesNotExist: return None
    def rename(self, name: str) -> bool:
        if self.get(name): return False
        old_wrap = self.wrap
        self.name = name
        self.save()
        for text in TextChange.objects.all():
            text.content = text.content.replace(old_wrap, self.wrap)
            text.save()
        return True
