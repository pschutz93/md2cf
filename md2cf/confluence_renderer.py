import mistune
import urllib.parse as urlparse
from pathlib import Path
import os
import re


class ConfluenceTag(object):
    def __init__(self, name, text="", attrib=None, namespace="ac", cdata=False):
        self.name = name
        self.text = text
        self.namespace = namespace
        if attrib is None:
            attrib = {}
        self.attrib = attrib
        self.children = []
        self.cdata = cdata
    def render(self):
        namespaced_name = self.add_namespace(self.name, namespace=self.namespace)
        namespaced_attribs = {
            self.add_namespace(
                attribute_name, namespace=self.namespace
            ): attribute_value
            for attribute_name, attribute_value in self.attrib.items()
        }

        content = "<{}{}>{}{}</{}>".format(
            namespaced_name,
            " {}".format(
                " ".join(
                    [
                        '{}="{}"'.format(name, value)
                        for name, value in sorted(namespaced_attribs.items())
                    ]
                )
            )
            if namespaced_attribs
            else "",
            "".join([child.render() for child in self.children]),
            "<![CDATA[{}]]>".format(self.text) if self.cdata else self.text,
            namespaced_name,
        )
        return "{}\n".format(content)

    @staticmethod
    def add_namespace(tag, namespace):
        return "{}:{}".format(namespace, tag)

    def append(self, child):
        self.children.append(child)


class ConfluenceRenderer(mistune.Renderer):
    def __init__(self, space="", **kwargs):
        super().__init__(**kwargs)
        self.attachments = list()
        self.title = None
        self.space = space

    def reinit(self):
        self.attachments = list()
        self.title = None

    def structured_macro(self, name):
        return ConfluenceTag("structured-macro", attrib={"name": name})

    def parameter(self, name, value):
        parameter_tag = ConfluenceTag("parameter", attrib={"name": name})
        parameter_tag.text = value
        return parameter_tag

    def plain_text_body(self, text):
        body_tag = ConfluenceTag("plain-text-body", cdata=True)
        body_tag.text = text
        return body_tag

    def block_code(self, code, lang=None):
        root_element = self.structured_macro("code")
        if lang is not None:
            lang_parameter = self.parameter(name="language", value=lang)
            root_element.append(lang_parameter)
        root_element.append(self.parameter(name="linenumbers", value="true"))
        root_element.append(self.plain_text_body(code))
        return root_element.render()

    def image(self, src, title, text):
        attributes = {"alt": text}
        if title:
            attributes["title"] = title

        root_element = ConfluenceTag(name="image", attrib=attributes)
        parsed_source = urlparse.urlparse(src)
        if not parsed_source.netloc:
            # Local file, requires upload
            unescaped = urlparse.unquote(src)
            basename = Path(unescaped).name
            url_tag = ConfluenceTag("attachment", attrib={"filename": basename}, namespace="ri")
            self.attachments.append(unescaped)
        else:
            url_tag = ConfluenceTag("url", attrib={"value": src}, namespace="ri")
        root_element.append(url_tag)

        return root_element.render()

    def link(self, link, text=None, title=None):
        if link[-3:] == '.md' or "notion.so" in link:
            result = urlparse.urlparse(link)
            baseName = os.path.basename(result.path)
            pageTitle=os.path.splitext(baseName)[0]
            pageTitle = pageTitle.replace("%20", "+")
            pageTitle = re.sub(r"[\(\)\[\]&{}]", "", pageTitle)

            link = "https://boltpay.atlassian.net/wiki/display/{space}/{title}".format(space=self.space, title=pageTitle)

        print("<a href=\"{link}\">{title}</a>".format(link=link, title=title))
        return "<a href=\"{link}\">{title}</a>".format(link=link, title=title)
