"""Decorators are awesome."""
from collections import OrderedDict
import threading
import functools
import time

from objdict import ObjectDict

class BaseDecorator(object):
    """
    Base class for all decorators. Simply initializes the attribute self.func
    and copies __doc__.
    """
    def __init__(self, func):
        self.func = func
        self.__doc__ = func.__doc__

# I thought I'd need this but I was wrong.

##class oneonly(BaseDecorator):
##    """
##    Decorator to prevent more than one instance of this function from being
##    executed at a time. If the function is called while another instance is
##    executing, the call will simply be abandoned and return None.
##    """
##    isCalling = False
##    def __call__(self, *args, **kwargs):
##        cls = self.__class__
##        if not cls.isCalling:
##            cls.isCalling = True
##            value = self.func(*args, **kwargs)
##            cls.isCalling = False
##            return value
##        else:
##            return None

##hits = 0
##total = 0
##
##def _memoizeAux(func, cache, args, kwargs, limit):
##    """Helper for memoized* decorators."""
##    global hits
##    global total
##    total += 1
##    try:
##        ans = cache[args, tuple(kwargs.items())]
##        hits += 1
##        print float(hits) / total
##        return ans
##    except KeyError:
##        value = func(*args, **kwargs)
##        if type(value) == str:
##            value = intern(value)
##        cache[args, tuple(kwargs.items())] = value
##        if limit and len(cache) > limit:
##            cache.popitem()
##        return value

def _memoizeAux(func, cache, args, kwargs, limit):
    """Helper for memoized* decorators."""
    try:
        return cache[args, tuple(kwargs.items())]
    except KeyError:
        value = func(*args, **kwargs)
        if type(value) == str:
            value = intern(value)
        cache[args, tuple(kwargs.items())] = value
        if limit and len(cache) > limit:
            cache.popitem()
        return value

class memoized(BaseDecorator):
    """
    Cache a function's return value each time it is called. If called later with
    the same arguments, the cached value is returned, and not re-evaluated.

    Also intern()s returned strings to save memory, in case other memoized
    functions return the same string.

    Note that you can access the cache OrderedDict with function._cache.

    Max of 100 cached items, once this is exceeded the oldest item is removed
    from cache whenever a new one is added.

    Modified from:
    http://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
    """
    def __init__(self, func):
        super(memoized, self).__init__(func)
        self._cache = OrderedDict()
    def __call__(self, *args, **kwargs):
        return _memoizeAux(self.func, self._cache, args, kwargs, 100)

def memoizedCustom(limit=100):
    """
    Same as memoized, but takes arguments:
    
    limit: max number of items to cache; use None for unlimited.
    """
    def realDecorator(fn):
        cache = {}
        def realFn(*args, **kwargs):
            return _memoizeAux(fn, cache, args, kwargs, limit)
        return realFn
    return realDecorator

def async(fn):
    """
    Decorator to run function in new daemon thread.
    
    The new function returns the Thread object and takes two additional keyword
    arguments, callback and callOnErr, which are called on the return value and
    any exception raised, respectively.
    
    If these are not provided, return value is ignored and exceptions are
    re-raised (and thus usually printed).
    """
    def newFunc(*args, **kwargs):
        def run():
            callback = kwargs.pop('callback', lambda x: None)
            callOnErr = kwargs.pop('callOnErr', None)

            try:
                callback(fn(*args, **kwargs))
            except Exception as err:
                if callOnErr:
                    callOnErr(err)
                else:
                    raise

        t = threading.Thread(target=run)
        t.daemon = True
        t.start()
        return t

    return newFunc

# for backwards compatibility
newthread = async

def lock(abandon=False):
    """
    Decorator to prevent more than one instance of this function from being
    executed at a time. Subsequent calls will be blocked until first one is
    finished.

    A waiting call will then execute if abandon is False, or simply return None
    without executing if abandon is True.
    """
    def locked(func):
        lock = threading.Lock()
        def lockFunc(*args, **kwargs):
            lock.acquire()
            value = func(*args, **kwargs)
            lock.release()
            return value
        return lockFunc
    def evented(func):
        event = threading.Event()
        # only set if function NOT running, so that event.wait() will block if
        # it is running
        event.set()
        def eventFunc(*args, **kwargs):
            if not event.isSet():
                event.wait()
                return None
            event.clear()
            value = func(*args, **kwargs)
            event.set()
            return value
        return eventFunc
    return evented if abandon else locked

def retry(ExceptionToCheck, maxTries=3, delay=1, mult=1, verbose=False,
        default=None):
    """
    Retry decorator using exponential backoff. If function still fails at the
    max number of tries, return default, else return result of function.

    ExceptionToCheck can be one Exception or multiple.

    Modified from:
    http://www.saltycrane.com/blog/2009/11/trying-out-retry-decorator-python/

    Which is itself modified from:
    http://wiki.python.org/moin/PythonDecoratorLibrary#Retry
    """
    def deco_retry(f):
        def f_retry(*args, **kwargs):
            curDelay = delay
            tries = 0
            while True:
                try:
                    return f(*args, **kwargs)
                except ExceptionToCheck, e:
                    tries += 1
                    if tries >= maxTries:
                        return default
                    if verbose:
                        print '%s, retrying in %f seconds...' % (e, curDelay)
                    time.sleep(curDelay)
                    curDelay *= mult
        return f_retry # true decorator
    return deco_retry

class threadedGenerator:
    """Decorator to transform a normal generator into a thread-safe one."""
    def __init__(self, gen):
        self.gen = gen
        self.lock = threading.RLock()
    def __call__(self, *args, **kwargs):
        self.it = self.gen(*args, **kwargs)
        return self
    def __iter__(self):
        return self
    def next(self):
        self.lock.acquire()
        try:
            item = self.it.next()
        finally:
            self.lock.release()
        return item

def reflector(func):
    """
    Decorator to add introspection to a function.

    Have the function take a "this" keyword, which will be set to the function
    itself and have attributes "args" and "kwargs", which do what you think.
    "kwargs" does not include "this".
    """
    def real(*args, **kwargs):
        this = func
        this.args = args
        this.kwargs = kwargs
        return func(this=this, *args, **kwargs)
    return real
