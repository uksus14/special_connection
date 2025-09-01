from xml.etree.ElementTree import Element, SubElement
from markdown.inlinepatterns import InlineProcessor
from markdown.blockprocessors import BlockProcessor
from utils import generate_core_id, get_user
from markdown.extensions import Extension
from images.models import Image
from re import PatternError
from typing import Callable
from utils import env
import regex as re
import markdown

users = lambda:{data["name"]: get_user(data["pk"]) for data in env["users"]}
reownership = lambda:fr":(?P<ownership>{'|'.join(['none', *users().keys(), 'both'])})"
reid = r"-(?P<id>(temp|[\p{L}\p{N}]{2})[\p{L}\p{N}]{2})"
redynamic = lambda:fr"{reownership()}{reid}"
restyles = r"(\[(?P<styles>[^\]]*)\])?"
template_dynamic = ":{ownership}-{id}"
reid_edit = fr"({reid})?"
redynamic_edit = lambda:fr"({reownership()}({reid})?)?"
retext = r"\(\((?P<text>([^)]+\)?)+)\)\)"

def parse_names(ownership: str):
    classes = ["user-dynamic", "pill"]
    if ownership == "both": classes += [f"pill-{user.pk}" for user in users().values()]
    if ownership in users(): classes.append(f"pill-{users()[ownership].pk}")
    return classes
def parse_styles(el: Element, styles: str):
    if not styles: return [], []
    styles = styles.split()
    for i, class_ in enumerate(styles):
        if ":" in class_:
            return styles[:i], styles[i:]
    return styles, []

class AutoInlineProcessor(InlineProcessor):
    NAME: str
    RE: Callable[[], str]
    TEMPLATE: str
    def handle(self, groups: dict[str, str], string: str) -> Element: raise NotImplementedError
    def handleMatch(self, m, data):
        groups = m.groupdict()
        return self.handle(groups, m.group(0)), m.start(0), m.end(0)
class AutoBlockProcessor(BlockProcessor):
    NAME: str
    RE_FENCE_START: str
    RE_LINE: Callable[[], str]
    LINE_TEMPLATE: str
    def test(self, parent, block):
        return re.match(self.RE_FENCE_START, block.partition("\n")[0].strip())
    def run(self, parent, blocks):
        block = blocks.pop(0).split("\n")
        root_data = re.match(self.RE_FENCE_START, block[0]).groupdict()
        el = self.create(**root_data)
        parent.append(el)
        self.fill(el, block[1:])
    def create(self, **kwargs) -> Element:
        raise NotImplementedError
    def fill(self, parent: Element, lines: list[str]):
        self.parser.parseBlocks(parent, lines)
    def generate_line(self, line: str) -> Element:
        raise NotImplementedError
        

class AutoExtension(Extension):
    INLINE_PROCESSORS: list[AutoInlineProcessor] = []
    BLOCK_PROCESSORS: list[AutoBlockProcessor] = []
    def extendMarkdown(self, md):
        for processor in self.INLINE_PROCESSORS:
            md.inlinePatterns.register(processor(processor.RE(), md), processor.NAME, 175)
        for processor in self.BLOCK_PROCESSORS:
            md.parser.blockprocessors.register(processor(md.parser), processor.NAME, 175)

class ImageProcessor(AutoInlineProcessor):
    NAME = "inline-image"
    RE = lambda*_:fr'!image\((?P<src>[^)]+)\){restyles}'
    TEMPLATE = "!image({src})[{styles}]"
    def handle(self, groups: dict[str, str], string: str):
        src = groups["src"]
        image = Image.get(src)
        if image: src = image.url
        el = Element("img")
        el.set("src", src)
        classes, styles = parse_styles(el, groups["styles"])
        el.set("class", " ".join(classes))
        el.set("style", " ".join(styles))
        return el

class StaticExtension(AutoExtension):
    INLINE_PROCESSORS = [ImageProcessor]

class UserSpanProcessor(AutoInlineProcessor):
    NAME = "user-span"
    RE = lambda*_:fr'!span{redynamic()}{retext}'
    TEMPLATE = f"!span{template_dynamic}(({{text}}))"
    def handle(self, groups: dict[str, str], string: str):
        id = groups["id"]
        el = Element("span")
        el.set("class", " ".join(parse_names(groups["ownership"])))
        el.set("id", f"core-{id}")
        el.set("onclick", f"coreToggle('{id}')")
        el.text = groups["text"].strip()
        return el

class UserListProcessor(AutoBlockProcessor):
    NAME = "user-list"
    RE_FENCE_START = fr"!list{restyles}"
    RE_LINE = lambda*_:fr"{redynamic()} *(?P<text>.*)"
    LINE_TEMPLATE = fr"{template_dynamic} {{text}}"
    def create(self, styles: str):
        el = Element("div")
        classes, styles = parse_styles(el, styles)
        classes.append("list")
        el.set("class", " ".join(classes))
        el.set("style", " ".join(styles))
        return el
    def fill(self, parent: Element, lines: list[str]):
        for line in lines:
            el = self.generate_line(line)
            if el: parent.append(el)
    def generate_line(self, line):
        groups = re.match(self.RE_LINE(), line).groupdict()
        id = groups["id"]
        el = Element("div")
        dot = Element("div")
        dot.set("id", f"core-{id}")
        dot.set("class", " ".join(["ownership-dot"]+parse_names(groups["ownership"])))
        dot.set("onclick", f"coreToggle('{id}')")
        el.append(dot)
        text = Element("div")
        self.parser.parseChunk(text, groups["text"].strip())
        el.append(text)
        return el

class DynamicExtension(AutoExtension):
    INLINE_PROCESSORS = [UserSpanProcessor]
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
    answer = []
    while lines:
        for processor in DynamicExtension.BLOCK_PROCESSORS:
            if not re.match(processor.RE_FENCE_START, lines[0]): continue
            answer.append(lines.pop(0))
            while lines and lines[0].strip():
                answer.append(inline(lines.pop(0).strip(), processor.RE_LINE(), processor.LINE_TEMPLATE))
            break
        if lines: answer.append(lines.pop(0))
    content = "\n".join(answer)
    for processor in DynamicExtension.INLINE_PROCESSORS:
        edit_re = processor.RE().replace(redynamic(), redynamic_edit())
        if not edit: edit_re = processor.RE()
        for match in re.finditer(edit_re, content):
            line = match.group(0)
            new_line = inline(line, processor.RE(), processor.TEMPLATE)
            if new_line != line: content = content.replace(line, new_line)
    return content
def setup_temp(content: str) -> str:
    def inline(line: str, RE: str, TEMPLATE: str) -> str:
        groups = re.match(RE.replace(redynamic(), redynamic_edit()), line).groupdict()
        if groups["id"] and groups["ownership"]: return line
        groups["id"] = groups["id"] or "temp"+generate_core_id(2)
        groups["ownership"] = groups["ownership"] or "none"
        return TEMPLATE.format(**groups)
    return handle_temp(content, inline, True)
def replace_temp(content: str) -> str:
    def inline(line: str, RE: str, TEMPLATE: str) -> str:
        groups = re.match(RE, line).groupdict()
        if not groups["id"].startswith("temp"): return line
        groups["id"] = generate_core_id(4)
        return TEMPLATE.format(**groups)
    return handle_temp(content, inline, False)