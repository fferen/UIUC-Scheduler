import urllib2
import logging

DEFAULT_USER_AGENT = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv:10.0) Gecko/20100101 Firefox/10.0'

def urlopenUA(url, userAgent=DEFAULT_USER_AGENT, *args, **kwargs):
    """Same as urllib2.urlopen(), but with option to set user agent."""
    req = urllib2.Request(
            url,
            headers={'User-Agent': userAgent},
            *args,
            **kwargs
            )
    logging.info(url)
    return urllib2.urlopen(req)

def oneFromEach(lists, conflicts):
    """
    >>> print oneFromEach(((1, 2, 3), (5,), (5,)), lambda a, b: a == b)
    None
    >>> print oneFromEach(((1, 5), (5,), (5, 1, 2)), lambda a, b: a == b)
    """
    def inner(lists, existing=[]):
        if not lists:
            return []
        for e in lists[0]:
            if not any(conflicts(e, exE) for exE in existing):
                try:
                    ans = [e] + inner(lists[1:], existing + [e])
                except ValueError:
                    pass
                else:
                    return ans
        raise ValueError('no solution')

    return inner(sorted(lists, key=len))

if __name__ == '__main__':
    import doctest
    doctest.testmod()
