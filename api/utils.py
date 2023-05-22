#!/usr/bin/env python
import sys
import random
import json
import marko
import marko.ast_renderer


def buttonify(links):
    buttons = [
        {"type": "button", "text": {"type": "plain_text", "text": title}, "url": url}
        for (url, title) in links
    ]
    random.shuffle(buttons)
    return buttons


SERVERS = [
    ("https://usegalaxy.eu/", "Galaxy Europe :earth_africa:"),
    ("https://usegalaxy.org/", "Galaxy US :earth_americas:"),
    ("https://usegalaxy.org.au/", "Galaxy Australia :earth_asia:"),
    # ("https://usegalaxy.be/", "Galaxy Belgium :flag-be:"),
    # ("https://usegalaxy.fr/", "Galaxy France :flag-fr:"),
]

TIAAS = [
    ("https://usegalaxy.eu/join-training/smorgasbord3/", "Join EU TIaaS :earth_africa:"),
    (
        "https://usegalaxy.org/join-training/smorgasbord3/",
        "Join US TIaaS :earth_americas:",
    ),
    ("https://usegalaxy.org.au/join-training/smorgasbord3/", "Join AU TIaaS :earth_asia:"),
    # ("https://usegalaxy.fr/join-training/gcc2022/", "Join FR TIaaS :flag-fr:"),
]


def render_paragraph(children):
    text = ""
    for kid in children:
        if kid["element"] == "raw_text":
            text += kid["children"]
        elif kid["element"] == "link":
            text += f"<{kid['dest']}|{kid['children'][0]['children']}>"
        elif kid["element"] == "strong_emphasis":
            text += f"*{kid['children'][0]['children']}*"
        elif kid["element"] == "emphasis":
            text += f"_{kid['children'][0]['children']}_"
        else:
            raise Exception(f"Unhandled: {kid}")
    return text


def convert_text(text):
    markdown = marko.Markdown(renderer=marko.ast_renderer.ASTRenderer)
    doc = markdown.convert(text)
    return convert_markodoc(doc)


def convert_markodoc(doc):
    blocks = []
    blocks_obj = {"blocks": blocks}

    for kid in doc["children"]:
        if kid["element"] == "heading":
            blocks.append(
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": kid["children"][0]["children"],
                    },
                }
            )
        elif kid["element"] == "blank_line":
            continue
        elif kid["element"] == "paragraph":
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": render_paragraph(kid["children"]),
                    },
                }
            )
        elif kid["element"] == "quote":
            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "> " + render_paragraph(kid["children"][0]["children"]),
                    },
                }
            )
        elif kid["element"] == "list":
            text = ""
            for idx, list_element in enumerate(kid["children"]):
                list_item = list_element["children"]
                text += "• " if kid["ordered"] is False else f"{idx}. "
                text += render_paragraph(list_item[0]["children"]) + "\n"

            blocks.append(
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": text,
                    },
                }
            )
        elif kid["element"] == "thematic_break":
            blocks.append(
                {
                    "type": "divider",
                }
            )
        elif kid["element"] == "html_block":
            text = kid["children"].strip()
            if text == "<SERVERS>":
                blocks.append({"type": "actions", "elements": buttonify(SERVERS)})
            elif text == "<TIAAS>":
                blocks.append({"type": "actions", "elements": buttonify(TIAAS)})
            else:
                raise Exception(f"Cannot handle {kid['children']}")

        else:
            raise Exception(f"Cannot handle {kid}")

    return blocks_obj
