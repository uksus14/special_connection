from django.contrib.auth.models import AbstractUser
from django.http import HttpRequest, HttpResponse
from utils import slugify, log, from_time, env
from django.shortcuts import redirect, render
from django.db import models, IntegrityError
from typing import Self, Callable
from django.urls import reverse
from datetime import datetime
from string import hexdigits
from random import choice

class User(AbstractUser):
    @property
    def color(self) -> str: return self.env.get("color", "")
    @property
    def name(self) -> str: return self.env.get("name", "")
    @property
    def env(self) -> dict[str, str|int]:
        for user in env["users"]:
            if int(user["pk"]) == self.pk:
                return user
        env["users"].append({"pk": self.pk})
        return env[-1]
    
class Change(models.Model):
    markdown = models.ForeignKey('Markdown', null=True, on_delete=models.SET_NULL)
    author = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)
    time = models.DateTimeField(auto_now_add=True, blank=True)
    @property
    def first(self) -> Self:
        return type(self).objects.filter(markdown=self.markdown).first()
    @property
    def last(self) -> Self:
        return type(self).objects.filter(markdown=self.markdown).last()
    @classmethod
    def all_history(cls, year: int=None, month: int=None) -> list[Self]:
        time_constraints = {}
        if year is not None: time_constraints['time__year'] = int(year)
        if month is not None: time_constraints['time__month'] = int(month)+1
        return list(cls.objects.filter(**time_constraints))
    def history(self, year: int=None, month: int=None) -> list[Self]:
        time_constraints = {}
        if year is not None: time_constraints['time__year'] = int(year)
        if month is not None: time_constraints['time__month'] = int(month)+1
        return list(type(self).objects.filter(markdown=self.markdown, **time_constraints))
    def slice(self, time: datetime) -> Self:
        return type(self).objects.filter(markdown=self.markdown, time__lte=time).last()
    class Meta:
        abstract = True

class DowntimeChange(Change):
    end = models.DateTimeField(blank=True, null=True)
    previous: 'DowntimeChange' = models.ForeignKey('self', related_name='previous_downtime', blank=True, null=True, on_delete=models.SET_NULL)
    next: 'DowntimeChange' = models.ForeignKey('self', related_name='next_downtime', blank=True, null=True, on_delete=models.SET_NULL)
    class Meta: ordering = ['time']
class TextChange(Change):
    content = models.TextField(blank=True)
    previous: 'TextChange' = models.ForeignKey('self', related_name='previous_text', blank=True, null=True, on_delete=models.SET_NULL)
    next: 'TextChange' = models.ForeignKey('self', related_name='next_text', blank=True, null=True, on_delete=models.SET_NULL)
    class Meta: ordering = ['time']
class TitleChange(Change):
    content = models.CharField(max_length=200)
    previous: 'TitleChange' = models.ForeignKey('self', related_name='previous_title', blank=True, null=True, on_delete=models.SET_NULL)
    next: 'TitleChange' = models.ForeignKey('self', related_name='next_title', blank=True, null=True, on_delete=models.SET_NULL)
    class Meta: ordering = ['time']
class OwnershipChange(Change):
    owners = models.ManyToManyField('User', related_name='owners')
    previous: 'OwnershipChange' = models.ForeignKey('self', related_name='previous_ownership', null=True, on_delete=models.SET_NULL)
    next: 'OwnershipChange' = models.ForeignKey('self', related_name='next_ownership', null=True, on_delete=models.SET_NULL)
    class Meta: ordering = ['time']

slice_cache: dict[str, 'MarkdownSlice'] = {}
class Markdown(models.Model):
    index_name = models.CharField(max_length=50, unique=True)
    title = models.ForeignKey(TitleChange, related_name='current_title', blank=True, null=True, on_delete=models.SET_NULL)
    downtime = models.ForeignKey(DowntimeChange, related_name='current_downtime', blank=True, null=True, on_delete=models.SET_NULL)
    text = models.ForeignKey(TextChange, related_name='current_text', blank=True, null=True, on_delete=models.SET_NULL)
    active = models.BooleanField(blank=True, default=True)
    ownership = models.ForeignKey(OwnershipChange, related_name='current_ownership', blank=True, null=True, on_delete=models.SET_NULL)
    seen = models.ManyToManyField(User, related_name='user_seen', blank=True)
    edited = models.DateTimeField(auto_now_add=True, blank=True)
    class Meta:
        ordering = ['-edited']
    @property
    def index(self) -> str:
        return f"{self.pk}-{self.index_name}.md"
    @property
    def url(self) -> str: return self.urlfor('c')
    def urlfor(self, reality: str) -> str:
        """reality should be either e, c or tm"""
        if reality not in ['e', 'c', 'tm']: raise Exception(f"{reality} is not a reality")
        return reverse(f"{reality}_markdown", kwargs={'pk': self.pk, 'index': self.index_name})
    @classmethod
    def all_changes(cls, year: int=None, month: int=None, include_downtime: bool=True) -> list[Change]:
        last = TitleChange, TextChange, OwnershipChange, DowntimeChange
        if not include_downtime: last = last[:-1]
        return sorted(sum(map(lambda c: c.all_history(year, month), last), []), key=lambda c: c.time)
    def changes(self, year: int=None, month: int=None, include_downtime: bool=True) -> list[Change]:
        last = self.last_changes
        if not include_downtime: last = last[:-1]
        return sorted(sum(map(lambda c: c.history(year, month), last), []), key=lambda c: c.time)
    @property
    def last_changes(self) -> tuple[Change]:
        return self.title, self.text, self.ownership, self.downtime
    @property
    def first_time(self) -> datetime:
        return max(map(lambda c:c.first.time, self.last_changes))
    @property
    def first(self) -> 'MarkdownSlice':
        return self.slice(self.first_time)
    @property
    def lastc(self) -> Change:
        return max(*self.last_changes, key=lambda c:c.time)
    @property
    def last(self) -> 'MarkdownSlice':
        return self.slice(self.lastc.time)
    @property
    def downtimes(self) -> list[DowntimeChange]:
        return DowntimeChange.objects.filter(markdown=self)
    @classmethod
    def slice_all(cls, time: datetime) -> list['MarkdownSlice']:
        return list(filter(None, (markdown.slice(time) for markdown in cls.objects.all())))
    def slice(self, time: datetime) -> 'MarkdownSlice':
        key = f'{self.pk}-{time}'
        if key in slice_cache: return slice_cache[key]
        if time > datetime.now(): return self.last
        title = self.title.slice(time)
        if title is None: return None
        downtime = self.downtime.slice(time)
        text = self.text.slice(time)
        ownership = self.ownership.slice(time)
        slice_cache[key] = MarkdownSlice(markdown=self, time=time, title=title,
            downtime=downtime, text=text, ownership=ownership)
        return slice_cache[key]
    @classmethod
    def handle_request(cls, func: Callable[[HttpRequest, Self], HttpResponse]) -> Callable[[HttpRequest, int, str], HttpResponse]:
        def view(request: HttpRequest, pk: int, index: str, **kwargs) -> HttpResponse:
            try: markdown = cls.objects.get(pk=pk)
            except cls.DoesNotExist: return render(request, '404.html', status=404)
            if request.GET.get('force', 'false').lower() == 'true':
                markdown.index_name = index
                markdown.save()
            log(f"{request.get_full_path()} seen by {request.user.name} at {from_time(datetime.now())}")
            if markdown.index_name == index: return func(request, markdown, **kwargs)
            return redirect(request.resolver_match.view_name, pk=pk, index=markdown.index_name, **kwargs, permanent=True)
        return view
    @classmethod
    def empty(cls, title: str, owner: User) -> Self:
        title = title.strip()
        title = title[0].capitalize() + title[1:]
        orig = index_name = slugify(title)
        while True:
            try: markdown = cls.objects.get(index_name=index_name)
            except cls.DoesNotExist:
                markdown = cls.objects.create(index_name=index_name)
                markdown.title = TitleChange.objects.create(markdown=markdown, author=owner, content=title)
                markdown.downtime = DowntimeChange.objects.create(markdown=markdown, author=owner)
                markdown.active = False
            if not markdown.active: break
            if orig == index_name: index_name += "_"
            index_name += choice(hexdigits)
        markdown.revive(owner)
        markdown.ownership = OwnershipChange.objects.create(markdown=markdown, author=owner)
        markdown.transfer(owner)
        markdown.text = TextChange.objects.create(markdown=markdown, author=owner, content='')
        markdown._changed(owner)
        return markdown
    def _changed(self, user: User):
        self.seen.clear()
        self.seen.add(user)
        self.edited = datetime.now()
        self.save()
    def rename(self, title: str, user: User):
        if title == self.title.content: return
        self.title.next = TitleChange.objects.create(markdown=self, author=user, previous=self.title, content=title)
        self.title.save()
        self.title = self.title.next
        self._changed(user)
    def transfer(self, user: User):
        self.ownership.next = OwnershipChange.objects.create(markdown=self, author=user, previous=self.ownership)
        self.ownership.save()
        self.ownership = self.ownership.next
        for owner in self.ownership.previous.owners.all():
            self.ownership.owners.add(owner)
        if self.ownership.owners.contains(user):
            self.ownership.owners.remove(user)
        else: self.ownership.owners.add(user)
        self.ownership.save()
        self._changed(user)
    def revive(self, user: User):
        if self.active: raise IntegrityError()
        self.downtime.end = datetime.now()
        self.downtime.save()
        self.active = True
        self._changed(user)
    def delete(self, user: User):
        if not self.active: raise IntegrityError()
        self.downtime.next = DowntimeChange.objects.create(markdown=self, author=user, previous=self.downtime)
        self.downtime.save()
        self.downtime = self.downtime.next
        self.active = False
        self._changed(user)
    def force_delete(self):
        super().delete()
    def change(self, content: str, user: User):
        from special_connection.render import replace_temp, setup_temp
        content = replace_temp(setup_temp(content))
        if content == self.text.content: return
        self.text.next = TextChange.objects.create(markdown=self, author=user, content=content, previous=self.text)
        self.text.save()
        self.text = self.text.next
        self._changed(user)
        return content

import copy
from dataclasses import dataclass

@dataclass
class MarkdownSlice:
    markdown: Markdown
    time: datetime
    title: TitleChange
    downtime: DowntimeChange
    text: TextChange
    ownership: OwnershipChange
    def __post_init__(self):
        self.pk = self.markdown.pk
        self.active = self.downtime.end and (self.downtime.end < self.time)
        self.url = self.markdown.urlfor('tm') + f"?time={from_time(self.time)}"
        self.set_both()
    
    @property
    def index_name(self) -> str: return self.markdown.index_name
    @property
    def index(self) -> str: return self.markdown.index

    def set_both(self):
        self.set_last()
        self.set_next()

    def set_last(self):
        self.lastc = max(self.title, self.downtime, self.text, self.ownership, key=lambda c:c.time)
        self.edited = self.lastc.time
        if self.active and self.edited < self.downtime.end:
            self.edited = self.downtime.end
            self.lastc = self.downtime
    def set_next(self):
        self.nextc = min(filter(lambda c:c.next, (self.title, self.downtime, self.text, self.ownership)), key=lambda c:c.next.time, default=None)
        self.will_edit = None
        if self.nextc is None: return
        self.will_edit = self.nextc.time
        if not self.active: self.will_edit = self.downtime.end

    @property
    def prev(self) -> Self:
        prev_obj = copy.copy(self)
        for change in ['title', 'downtime', 'text', 'ownership']:
            if getattr(prev_obj, change) == prev_obj.lastc:
                setattr(prev_obj, change, prev_obj.lastc.previous)
                prev_obj.set_both()
                return prev_obj
    @property
    def next(self) -> Self:
        next_obj = copy.copy(self)
        for change in ['title', 'downtime', 'text', 'ownership']:
            if getattr(next_obj, change) == next_obj.nextc:
                setattr(next_obj, change, next_obj.nextc.next)
                next_obj.set_both()
                return next_obj