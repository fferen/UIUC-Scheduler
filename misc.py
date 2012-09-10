"""Random algorithms that are occasionally useful."""
import random
import math
import itertools
import time
import threading
import string
import urllib2
import os
import inspect

from decorators import memoized

ROMANS = 'I IV V IX X XL L XC C CD D CM M'.split()
NUMS = (1, 4, 5, 9, 10, 40, 50, 90, 100, 400, 500, 900, 1000)

def longestPrefix(seqs):
    """Return the longest common prefix of all the sequences."""
    i = 0
    for i in xrange(min(len(s) for s in seqs) + 1):
        try:
            if not all(s[i] == seqs[0][i] for s in seqs):
                break
        except IndexError:
            break
    return seqs[0][:i]

def longestSuffix(strs):
    """Return the longest common suffix of all the sequences."""
    return longestPrefix([s[::-1] for s in strs])[::-1]

def getContext(ioPairs):
    """
    Given a iterable of IO tuples:

        (input sequence, desired output subsequence)

    Return the longest common output context as (prefix, suffix) tuple.
    """
    surroundTups = []
    for inp, out in ioPairs:
        i = inp.find(out)
        if i == -1:
            raise ValueError('output not found in input: (%s, %s)' % (inp, out))
        surroundTups.append((inp[:i], inp[i + len(out):]))
    return (longestSuffix([a for a, b in surroundTups]),
            longestPrefix([b for a, b in surroundTups]))

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
        return f_retry
    return deco_retry

class printDisabled(object):
    """
    Run some code with the print statement disabled.

    You can use it with the `with` statement:
    
        with printDisabled():
            print 'hi'

    or as a decorator:

        @printDisabled
        def func():
            print 'hi'

    Hooray!
    """
    def __init__(self, func=None):
        self.func = func
    def __call__(self, *args, **kwargs):
        with printDisabled():
            self.func(*args, **kwargs)
    def __enter__(self):
        self.stdoutSave = sys.stdout

        class Dummy:
            def write(self, *args, **kwargs):
                pass
        sys.stdout = Dummy()
    def __exit__(self, type, val, trace):
        sys.stdout = self.stdoutSave

def strFry(s):
    """Return s scrambled."""
    sList = list(s)
    random.shuffle(sList)
    return ''.join(sList)

def badMedian(l):
    """
    Approximate the median of l using a pretty screwy hill-climbing algorithm.
    If l has an even number of elements, return some number in between the two
    center ones.
    """
    def getError(l, num):
        return sum([abs(l[i] - num) for i in xrange(len(l))])

    allMod1 = [x % 1 for x in l if x % 1 != 0]

    CHANGED = 0.001 if len(allMod1) == 0 else min(allMod1)

    curNum = random.uniform(min(l), max(l))

    lastErr = 0

    while True:
        startErr = getError(l, curNum)
        lowErr = getError(l, curNum - CHANGED)
        highErr = getError(l, curNum + CHANGED)
        minErr = min(startErr, lowErr, highErr)
        if minErr == lowErr:
            curNum -= CHANGED
        elif minErr == highErr:
            curNum += CHANGED
        if abs(lastErr - minErr) < 0.0001:
            return curNum
        lastErr = minErr

def genAllPerms(chars, minLen, maxLen):
    """
    Yield all permutations of chars by increasing length, with repeats.

    If chars is a str, yields str, else list.
    """
    for l in xrange(minLen, maxLen + 1):
        gen = itertools.product(chars, repeat=l)
        while True:
            try:
                if type(chars) == str:
                    yield ''.join(gen.next())
                else:
                    yield list(gen.next())
            except StopIteration:
                break

def lcs(xs, ys):
    """Return a longest common subsequence of xs and ys."""
    if not xs or not ys:
        return []
    if xs[-1] == ys[-1]:
        return lcs(xs[:-1], ys[:-1]) + [xs[-1]]
    return max(lcs(xs[:-1], ys), lcs(xs, ys[:-1]), key=len)

def weightedChoice(l):
    """
    Given a list of values, return index i with a probability proportional to
    l[i].
    """
    try:
        l = [float(elem) / sum(l) for elem in l]
    except ZeroDivisionError:
        # all elements are zero
        return random.randint(0, len(l) - 1)
    else:
        n = random.random()
        for i, prob in enumerate(l):
            if n < prob:
                return i
            n -= prob
        raise ValueError, 'invalid list'

def getBackgroundInput(callback):
    """
    Run a background thread that calls callback with any input on stdin.
    
    Useful for quickly adding interactivity to a script.
    """
    def func():
        while True:
            callback(raw_input())
    thr = threading.Thread(target=func)
    thr.daemon = True
    thr.start()

def remDupsOrdered(l):
    """Return l with duplicates removed and order preserved."""
    new = []
    for elem in l:
        if elem not in new:
            new.append(elem)
    return new

def baseConvert(n, start, end, chars=string.digits + string.ascii_lowercase):
    """
    Interpret an integer or string in base <start> and return a string in base
    <end>, using <chars>, which by default is
    '0123456789abcdefghijklmnopqrstuvwxyz'.

    >>> baseConvert(50, 10, 5)
    '200'
    >>> baseConvert(50, 9, 12)
    '39'
    >>> baseConvert('50', 9, 12)
    '39'
    >>> baseConvert('a0', 18, 10)
    '180'
    >>> baseConvert('abc', 10, 7, chars='abcdefghij')
    'bf'
    >>> baseConvert('abc', 10, 7, chars='abc')
    Traceback (most recent call last):
        ...
    ValueError: generated digit 5 exceeds length of chars
    """
    def getIntN():
        s = 0
        for i, c in enumerate(n[::-1]):
            try:
                s += chars.index(c) * (start ** i)
            except ValueError:
                raise ValueError, '"%s" not in chars' % c
        return s

    if start < 2 or end < 2:
        raise ValueError, 'start and end base must be >=2.'

    n = str(n)

    if chars == string.digits + string.ascii_lowercase:
        try:
            intN = int(n, start)
        except ValueError:
            intN = getIntN()
    else:
        intN = getIntN()

    nums = [1]
    for power in counter(1):
        new = end ** power
        if new > intN:
            break
        nums.append(new)

    result = []
    for n in reversed(nums):
        digit, intN = divmod(intN, n)
        try:
            result.append(chars[digit])
        except IndexError:
            raise ValueError, \
                    'generated digit %d exceeds length of chars' % digit

    return ''.join(result)

def getCounts(l):
    """Return a list of tuples (elem, count) for elements in l."""
    return [(elem, l.count(elem)) for elem in set(l)]

def isNumber(s):
    """
    Return True if string is a number. Intended for only loose validation.
    
    >>> isNumber('100')
    True
    >>> isNumber('1.5e-10')
    True
    >>> isNumber('h32n4s')
    False
    >>> isNumber('100,000')
    True
    >>> isNumber('100, 000')
    False
    >>> isNumber('10000,00000')
    True
    """
    try:
        float(s.replace(',', ''))
    except ValueError:
        return False
    return True

@retry(urllib2.HTTPError, maxTries=5, delay=0.5, mult=2, verbose=True)
def urlopenWithRetry(*args, **kwargs):
    """
    Same as urllib2.urlopen(), but retries up to 5 times in case of HTTPError.
    Return None if it still fails after 5 tries.
    """
    return urllib2.urlopen(*args, **kwargs)

def toRoman(n):
    """
    Return the minimum length Roman numeral for integer n.

    Today I learned Roman numerals actually have many silly rules, listed here:
    http://projecteuler.net/about=roman_numerals

    They could be so much more efficient!
    
    >>> toRoman(1)
    'I'
    >>> toRoman(42)
    'XLII'
    >>> toRoman(349)
    'CCCXLIX'
    """
    for roman, testN in reversed(zip(ROMANS, NUMS)):
        if testN <= n:
            return roman if testN == n else roman + toRoman(n - testN)

def fromRoman(rn):
    """
    Return integer of Roman numeral string rn.

    >>> fromRoman('I')
    1
    >>> fromRoman('XLII')
    42
    >>> fromRoman('CCCXLIX')
    349
    """
    ROMAN_TO_NUM = dict(zip(ROMANS, NUMS))
    n = 0
    while rn:
        try:
            # handle subtractive pairs
            n += ROMAN_TO_NUM[rn[:2]]
            rn = rn[2:]
        except KeyError:
            n += ROMAN_TO_NUM[rn[0]]
            rn = rn[1:]
    return n

def aStarSearch(startNode, goalNode, getNeighbors, getDist, getHeuristicCost):
    """
    Implementation of the A* search algorithm.

    Return (list of nodes from startNode to goalNode, total cost).

    getNeighbors(node) takes a node and returns an iterable of neighbors.
    getDist(node1, node2) returns the distance between two adjacent nodes.
    getHeuristicCost(node) returns distance estimate from node to goal.

    Nodes must be hashable. Heuristic must be consistent
    (http://en.wikipedia.org/wiki/Consistent_heuristic).
    """
    def getPath(node):
        """Return final list of nodes using ending node and nodeToPrevious."""
        if node in nodeToPrevious:
            return getPath(nodeToPrevious[node]) + [node]
        else:
            return [node]

    openNodes = {startNode}
    closedNodes = set()
    gScores = {startNode: 0}
    fScores = {startNode: getHeuristicCost(startNode)}

    nodeToPrevious = dict()

    while openNodes:
        lowestNode = min((fScores[node], node) for node in openNodes)[1]
        if lowestNode == goalNode:
            return (getPath(goalNode), gScores[goalNode])
            
        openNodes.remove(lowestNode)
        closedNodes.add(lowestNode)

        for neighbor in getNeighbors(lowestNode):
            if neighbor in closedNodes:
                continue

            openNodes.add(neighbor)

            newG = gScores[lowestNode] + getDist(lowestNode, neighbor)
            if neighbor not in gScores or newG < gScores[neighbor]:
                gScores[neighbor] = newG
                fScores[neighbor] = newG + getHeuristicCost(neighbor)
                nodeToPrevious[neighbor] = lowestNode

    raise ValueError('no solution found')

def discretize(start, end, func, n=100):
    """
    Take n evenly-spaced samples of func with domain [start, end] and return:
    
    (list of domain values, list of range values)

    This will include values at start and end.
    """
    added = float(end - start) / (n - 1)

    domain = [start + added * i for i in xrange(n - 1)] + [end]
    rng = [func(x) for x in domain]
    return domain, rng

def genPOS(words, pos):
    """Generate words whose part of speech is pos, forever."""
    import nltk

    while True:
        word = random.choice(words)
        if nltk.pos_tag((word,))[0][1] == pos:
            return word

def minSampleSize(prop, prec=-1):
    """
    Return the minimum sample size that could generate a (rounded) proportion.
    """
    if prec == -1:
        prec = len(str(prop)) - 2
    for pop in counter(1):
        for samp in xrange(pop):
            if round(float(samp) / pop, prec) == prop:
                return pop

def fmtBin(n, minBytes=1):
    """
    Return the binary representation of n, padded to at least minBytes bytes
    with each byte separated by spaces.
    """
    s = bin(n)[2:]
    s = s.rjust(max(minBytes, int(math.ceil(len(s) / 8.0))) * 8, '0')
    return ' '.join(s[i:i + 8] for i in xrange(0, len(s), 8))

def getTempFileName(length=10):
    """
    Return a file name in this form: '.temp_<random letters>'

    Don't use this: use the tempfile module instead.
    """
    return '.temp_' + ''.join(
            random.choice('abcdefghijklmnopqrstuvwxyz') for i in xrange(length)
            )

def getCombMasks(n):
    """
    This is best shown by example:

    >>> getCombMasks(3)
    ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 0), (1, 0, 1), (0, 1, 1), (1, 1, 1))
    """
    combs = [[t for t in itertools.combinations(xrange(n), k)] \
            for k in xrange(n + 1)]

    masks = []
    for c in combs:
        for a in c:
            masks.append(tuple(1 if x in a else 0 for x in xrange(n)))

    return tuple(masks)

def isDynamicallyScoped():
    """
    Test if Python is dynamically scoped.

    >>> isDynamicallyScoped()
    False
    """
    def inner():
        g += 1
    def called():
        g = 3
        inner()
    try:
        called()
    except NameError:
        return False
    return True

def iterGroups(iterable, size):
    """
    Yield tuples of length `size` from iterable. Ignore any trailing elements.

    >>> [t for t in iterGroups([1, 2, 3, 4], 2)]
    [(1, 2), (3, 4)]
    >>> [t for t in iterGroups([2, 3, 3, 4, 5], 2)]
    [(2, 3), (3, 4)]
    """
    iterator = iter(iterable)
    while True:
        val = tuple(iterator.next() for i in xrange(size))
        if len(val) != size:
            break
        yield val

def applyToWindow(l, func):
    l = list(l)
    arity = len(inspect.getargspec(func)[0])
    for i in xrange(len(l) - arity + 1):
        l[i:i + arity] = func(*l[i:i + arity])
    return l

if __name__ == '__main__':
    import doctest

    doctest.testmod()
