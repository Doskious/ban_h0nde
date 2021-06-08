# -*- coding: utf-8 -*-
from frozendict import frozendict

ERRTS = 'YYYY-MM-dd HH:mm:ss'
UUID_CHAR = r'[0-9a-fA-F]'
UUID_REGEX_EXPR = (
    r'{0}{{8}}\-{0}{{4}}\-{0}{{4}}\-{0}{{4}}\-{0}{{12}}'.format(UUID_CHAR))
