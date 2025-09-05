from markdown.inlinepatterns import InlineProcessor
from markdown.blockprocessors import BlockProcessor
from utils import generate_core_id, get_user
from xml.etree.ElementTree import Element
from markdown.extensions import Extension
from images.models import Image
from re import PatternError
from typing import Callable
from utils import env
import regex as re
import markdown

users = lambda:{data["name"]: get_user(data["pk"]) for data in env["users"]}
def ownership_options(zero=False, single=False) -> list[str]:
    options = list(users().keys())
    if zero: options.append('zero')
    if not single: options.extend(['none', 'both'])
    return options
reownership = lambda zero=False, single=False:fr":(?P<ownership>{'|'.join(ownership_options(zero, single))})"
reid = r"-(?P<id>(temp|[\p{L}\p{N}]{2})[\p{L}\p{N}]{2})"
redynamic = lambda zero=False, single=False:fr"{reownership(zero, single)}{reid}"
restyles = r"(\[(?P<styles>[^\]]*)\])?"
template_ownership = ":{ownership}"
template_dynamic = ":{ownership}-{id}"
reid_edit = fr"({reid})?"
redynamic_edit = lambda zero=False, single=False:fr"({reownership(zero, single)}({reid})?)?"
retext = r"\(\((?P<text>([^)]+\)?)+)\)\)"

def parse_names(ownership: str):
    if ownership == 'zero': return []
    classes = ["user-dynamic", "pill"]
    if ownership == "both": classes += [f"pill-{user.pk}" for user in users().values()]
    if ownership in users(): classes.append(f"pill-{users()[ownership].pk}")
    return classes
def parse_styles(styles_str: str):
    if not styles_str: return [], []
    styles = styles_str.split()
    for i, class_ in enumerate(styles):
        if ":" in class_:
            return styles[:i], styles[i:]
    return styles, []

class AutoInlineProcessor(InlineProcessor):
    NAME: str
    default_owner = 'none'
    RE: Callable[..., str]
    TEMPLATE: str
    def handle(self, groups: dict[str, str], string: str) -> Element: raise NotImplementedError
    def handleMatch(self, m, data):
        groups = m.groupdict()
        return self.handle(groups, m.group(0)), m.start(0), m.end(0)
class AutoBlockProcessor(BlockProcessor):
    NAME: str
    default_owner = 'none'
    RE_FENCE_START: str
    RE_LINE: Callable[..., str]
    FENCE_END = ""
    LINE_TEMPLATE: str
    def test(self, parent, block):
        return re.match(self.RE_FENCE_START, block.partition("\n")[0].strip())
    def run(self, parent, blocks):
        block = blocks.pop(0).split("\n")
        root_data = re.match(self.RE_FENCE_START, block[0].strip()).groupdict()
        el = self.create(**root_data)
        if(self.FENCE_END):
            while blocks:
                if block[-1].strip() == self.FENCE_END:
                    block = block[:-1]
                    break
                block.extend(blocks.pop(0).split("\n"))
        self.fill(el, block[1:], root_data)
        parent.append(el)
    def create(self, **kwargs) -> Element:
        raise NotImplementedError
    def fill(self, parent: Element, lines: list[str], data: dict[str, str|None]):
        self.parser.parseBlocks(parent, lines)
    def generate_line(self, line: str, data: dict[str, str|None]) -> Element:
        raise NotImplementedError
        

class AutoExtension(Extension):
    INLINE_PROCESSORS: list[AutoInlineProcessor] = []
    BLOCK_PROCESSORS: list[AutoBlockProcessor] = []
    def extendMarkdown(self, md):
        for processor in self.INLINE_PROCESSORS:
            md.inlinePatterns.register(processor(processor.RE(dynamic=redynamic), md), processor.NAME, 175)
        for processor in self.BLOCK_PROCESSORS:
            md.parser.blockprocessors.register(processor(md.parser), processor.NAME, 175)

class StaticUserSpanProcessor(AutoInlineProcessor):
    NAME = "static-user-span"
    RE = lambda*_, **k:fr'!sspan({reownership(zero=True)})?{retext}{restyles}'
    TEMPLATE = f"!sspan{template_ownership}(({{text}}))[{{styles}}]"
    def handle(self, groups: dict[str, str], string: str):
        el = Element("span")
        classes, styles = parse_styles(groups["styles"])
        classes.extend(parse_names(groups["ownership"] or 'zero'))
        styles.append("cursor: default;")
        el.set("class", " ".join(classes))
        el.set("style", " ".join(styles))
        el.text = groups["text"].strip()
        return el

class ImageProcessor(AutoInlineProcessor):
    NAME = "inline-image"
    RE = lambda*_, **k:fr'!image\((?P<src>[^)]+)\){restyles}'
    TEMPLATE = "!image({src})[{styles}]"
    def handle(self, groups: dict[str, str], string: str):
        src = groups["src"]
        image = Image.get(src)
        if image: src = image.url
        el = Element("img")
        el.set("src", src)
        classes, styles = parse_styles(groups["styles"])
        el.set("class", " ".join(classes))
        el.set("style", " ".join(styles))
        return el
class ButtonProcessor(AutoInlineProcessor):
    NAME = "inline-button"
    RE = lambda*_, **k:fr'!btn({reownership()})?-(?P<id>[a-zA-Z0-9]+){retext}{restyles}'
    TEMPLATE = "!btn:{ownership}-{id}(({text}))[{styles}]"
    def handle(self, groups: dict[str, str], string: str):
        el = Element("button")
        if groups["id"]: el.set("id", groups["id"])
        classes, styles = parse_styles(groups["styles"])
        classes.append("interface-btn")
        classes.extend(parse_names(groups["ownership"] or 'none'))
        el.set("class", " ".join(classes))
        el.set("style", " ".join(styles))
        el.text = groups["text"]
        return el
class CSSProcessor(AutoBlockProcessor):
    NAME = "style"
    RE_FENCE_START = r"\[!style\]"
    RE_LINE = lambda*_, dynamic=0:r"(?P<text>.*)"
    FENCE_END = "[/style]"
    def create(self):
        return Element("style")
    def fill(self, parent: Element, lines: list[str], data: dict[str, str|None]):
        parent.text = self.parser.md.htmlStash.store("\n".join(lines))
class JSProcessor(AutoBlockProcessor):
    NAME = "script"
    RE_FENCE_START = r"\[!script\]"
    RE_LINE = lambda*_,**k:r"(?P<text>.*)"
    FENCE_END = "[/script]"
    LITERAL = True
    def create(self):
        return Element("script")
    def fill(self, parent: Element, lines: list[str], data: dict[str, str|None]):
        parent.text = self.parser.md.htmlStash.store(f"{{{'\n'.join(lines)}}}")

class StaticExtension(AutoExtension):
    INLINE_PROCESSORS = [StaticUserSpanProcessor, ImageProcessor, ButtonProcessor]
    BLOCK_PROCESSORS = [CSSProcessor, JSProcessor]

class UserSpanProcessor(AutoInlineProcessor):
    NAME = "user-span"
    RE = lambda*_, dynamic:fr'!span{dynamic()}{retext}'
    TEMPLATE = f"!span{template_dynamic}(({{text}}))"
    def handle(self, groups: dict[str, str], string: str):
        id = groups["id"]
        el = Element("span")
        el.set("class", " ".join(parse_names(groups["ownership"])))
        el.set("id", f"core-{id}")
        el.set("onclick", f"coreToggle('{id}')")
        el.text = groups["text"].strip()
        return el
class UserToggleSpanProcessor(AutoInlineProcessor):
    NAME = "user-toggle-span"
    default_owner = 'orange'
    RE = lambda*_, dynamic:fr'!toggle{dynamic(single=True)}{retext}'
    TEMPLATE = f"!toggle{template_dynamic}(({{text}}))"
    def handle(self, groups: dict[str, str], string: str):
        id = groups["id"]
        el = Element("span")
        el.set("class", " ".join(parse_names(groups["ownership"])))
        el.set("id", f"core-{id}")
        el.set("onclick", f"coreToggle('{id}', false, true)")
        el.text = groups["text"].strip()
        return el

class UserListProcessor(AutoBlockProcessor):
    NAME = "user-list"
    RE_FENCE_START = fr"!(?P<double>double-)?list{restyles}"
    RE_LINE = lambda*_, dynamic:fr"{dynamic()} *(?P<text>.*)"
    LINE_TEMPLATE = fr"{template_dynamic} {{text}}"
    def create(self, double: str|None, styles: str):
        el = Element("div")
        classes, styles = parse_styles(styles)
        classes.append("list")
        el.set("class", " ".join(classes))
        el.set("style", " ".join(styles))
        return el
    def fill(self, parent: Element, lines: list[str], data: dict[str, str|None]):
        for line in lines:
            el = self.generate_line(line, data)
            if el: parent.append(el)
    def generate_line(self, line: str, data: dict[str, str|None]):
        groups = re.match(self.RE_LINE(dynamic=redynamic), line).groupdict()
        id = groups["id"]
        el = Element("div")
        dot = Element("div")
        dot.set("id", f"core-{id}")
        dot.set("class", " ".join(["ownership-dot"]+parse_names(groups["ownership"])))
        dot.set("onclick", f"coreToggle('{id}', {str(bool(data['double'])).lower()}, false)")
        el.append(dot)
        text = Element("div")
        self.parser.parseChunk(text, groups["text"].strip())
        el.append(text)
        return el

class DynamicExtension(AutoExtension):
    INLINE_PROCESSORS = [UserSpanProcessor, UserToggleSpanProcessor]
    BLOCK_PROCESSORS = [UserListProcessor]

md = lambda:markdown.Markdown(extensions=[StaticExtension(), DynamicExtension()])

def render_markdown(content: str) -> str:
    try:
        parser = md()
    except PatternError:
        print("Find the file inlinepatterns.py and replace 'import re' with 'import regex as re'")
        quit()
    return parser.convert(content)

def handle_temp(content: str, inline: Callable[[str, str, str], str], edit: bool) -> str:
    lines = content.split("\n")
    dynamic = redynamic_edit if edit else redynamic
    answer = []
    while lines:
        for processor in DynamicExtension.BLOCK_PROCESSORS:
            if not re.match(processor.RE_FENCE_START, lines[0]): continue
            answer.append(lines.pop(0))
            while lines and lines[0].strip():
                answer.append(inline(lines.pop(0).strip(), processor.RE_LINE(dynamic=dynamic), processor.LINE_TEMPLATE, processor.default_owner))
            break
        if lines: answer.append(lines.pop(0))
    content = "\n".join(answer)
    for processor in DynamicExtension.INLINE_PROCESSORS:
        edit_re = processor.RE(dynamic=dynamic)
        for match in re.finditer(edit_re, content):
            line = match.group(0)
            new_line = inline(line, edit_re, processor.TEMPLATE, processor.default_owner)
            if new_line != line: content = content.replace(line, new_line)
    return content
def setup_temp(content: str) -> str:
    def inline(line: str, RE: str, TEMPLATE: str, default_owner: str='none') -> str:
        groups = re.match(RE, line).groupdict()
        if groups["id"] and groups["ownership"]: return line
        groups["id"] = groups["id"] or "temp"+generate_core_id(2)
        groups["ownership"] = groups["ownership"] or default_owner
        return TEMPLATE.format(**groups)
    return handle_temp(content, inline, True)
def replace_temp(content: str) -> str:
    def inline(line: str, RE: str, TEMPLATE: str, default_owner: str='none') -> str:
        groups = re.match(RE, line).groupdict()
        if not groups["id"].startswith("temp"): return line
        groups["id"] = generate_core_id(4)
        return TEMPLATE.format(**groups)
    return handle_temp(content, inline, False)