#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from collections import namedtuple

# Совместимость с Python 3.5: namedtuple без defaults; обёртка задаёт block_id по умолчанию.
_NodeInfo = namedtuple('NodeInfo', ['file_id', 'node_id', 'name', 'block_id'])

def node(file_id, node_id, name, block_id=None):
    if block_id is None:
        return _NodeInfo(file_id, node_id, name, None)
    return _NodeInfo(file_id, node_id, name, block_id)

