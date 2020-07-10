import lxml.etree

import cssselect


def to_string(node, strip=False):
    if isinstance(node, list):
        node = node[0]

    return lxml.etree.tostring(node, method="text", encoding=str)


def css(selector):
    return cssselect.GenericTranslator().css_to_xpath(selector)
