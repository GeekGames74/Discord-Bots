from sys import path as syspath
from os import path as ospath

root = ospath.abspath(ospath.join(ospath.dirname(__file__), '..'))

if root not in syspath:
    syspath.append(root)
