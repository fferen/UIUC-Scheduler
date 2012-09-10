from collections import defaultdict

class ObjectDict(defaultdict):
    """
    A defaultdict that also supports object access notation.

    >>> d = ObjectDict()
    >>> d['hi'] = 3
    >>> d.hi
    3
    >>> d.bye = 1
    >>> d['bye']
    1
    >>> d.nosuchthing
    Traceback (most recent call last):
    ...
    AttributeError: nosuchthing
    >>> d = ObjectDict(int)
    >>> d.a
    0
    """
    def __getattr__(self, attr):
        try:
            return self[attr]
        except KeyError:
            raise AttributeError, attr
    def __setattr__(self, attr, value):
        self[attr] = value

if __name__ == '__main__':
    import doctest

    doctest.testmod()
