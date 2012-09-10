from pprint import pprint
import urllib2
import re
from bs4 import BeautifulSoup
import itertools
from collections import defaultdict
import logging

from decorators import retry
import utils
import misc

DAYS = 'mtwrf'

def extractTableData(soup):
    """From soup of course page HTML, return a list of table rows."""
    for selector in ('table#table-alt-b', 'table.tablesorter', 'table.tableitems', 'table'):
        matches = soup.select(selector)
        if matches:
            tag = matches[0]
            break
    else:
        raise Exception('table element not found')

    rows = tag.select('tr')

    th = rows[0].select('th')
    if th:
        headers = [e.get_text() for e in th]
    else:
        raise Exception('table headers not found')
    
    secList = []
    for row in rows[1:]:
        elems = [e.get_text().strip() for e in row.select('td')]
        if len(elems) != len(headers):
            continue

        secList.append(dict(zip(headers, elems)))

    return secList

def urlopenPath(path):
    if not path.startswith('/'):
        path = '/' + path
    return utils.urlopenUA('https://courses.illinois.edu/cisapp/dispatcher' + path)

@retry(Exception)
def getSubCodes(year, season):
    html = urlopenPath('catalog/%d/%s' % (year, season.lower())).read()
    return re.findall(r'<td class="fl" title="([A-Z]{2,5})">\1</td>', html)

@retry(Exception)
def getCurYearSeason():
    html = urlopenPath('home').read()
    soup = BeautifulSoup(html)
    for tag in soup.select('p > a'):
        if tag.get_text().lower() == 'class schedule':
            path = tag.get('href')
            html = utils.urlopenUA('https://my.illinois.edu' + path)
            soup = BeautifulSoup(html)
            for tag in soup.select('a[href]'):
                url = tag.get('href')
                if url.startswith('https://courses.illinois.edu/cisapp/dispatcher/schedule/'):
                    _, year, season = url.rsplit('/', 2)
                    return (int(year), season)
    return None

@retry(Exception)
def getClassSections(subCode, num, year, season):
    html = urlopenPath('schedule/%d/%s/%s/%d' \
            % (year, season.lower(), subCode.upper(), num)).read()
    # work around malformed html that BeautifulSoup can't parse correctly (but
    # browsers can?!)
    html = html.replace('class="section-meeting"/>', 'class="section-meeting">')
    return extractTableData(BeautifulSoup(html))

@retry(Exception)
def getClasses(subCode, year, season):
    html = urlopenPath('schedule/%d/%s/%s' \
            % (year, season.lower(), subCode.upper())).read()
    return extractTableData(BeautifulSoup(html))

def overlaps(t1, t2):
    """
    >>> overlaps((1, 11, 00, 11, 50), (1, 10, 00, 10, 50))
    False
    >>> overlaps((1, 11, 00, 11, 50), (1, 10, 00, 11, 01))
    True
    >>> overlaps((1, 11, 00, 11, 50), (1, 10, 00, 11, 00))
    True
    """
    def between(hrMin, t):
        def toMins(hrMin):
            return hrMin[0] * 60 + hrMin[1]
        return toMins(t[1:3]) <= toMins(hrMin) <= toMins(t[3:5])

    if t1[0] != t2[0]:
        return False

    return between(t1[3:5], t2) or between(t2[3:5], t1)

def strToIntervals(s):
    """
    Given a string of days and time intervals in the following format, return a
    list of 5-tuples: (day index, start hour, start min, end hour, end min).

    >>> strToIntervals('MTW 10 10:50 11:00 11:50')
    [(0, 10, 0, 10, 50), (0, 11, 0, 11, 50), (1, 10, 0, 10, 50), (1, 11, 0, 11, 50), (2, 10, 0, 10, 50), (2, 11, 0, 11, 50)]
    """
    def getTimeTup(s):
        return tuple(int(t) for t in s.split(':')) if ':' in s else (int(s), 0)

    parts = s.lower().split()
    days = parts[0]
    timeIntervals = misc.iterGroups(parts[1:], 2)

    ivals = []
    for day, (startTime, endTime) in itertools.product(days, timeIntervals):
        ivals.append((DAYS.index(day.lower()),) \
                + getTimeTup(startTime) \
                + getTimeTup(endTime))
    return ivals

def reprInterval(ival):
    def reprTime(t):
        return '%02d:%02d %s' \
                % (t[0] - 12 if t[0] > 12 else t[0], t[1], 'PM' if t[0] >= 12 else 'AM')
    return '%s %s - %s' \
            % (DAYS[ival[0]].upper(), reprTime(ival[1:3]), reprTime(ival[3:5]))

def sectionToIntervals(section):
    def getHrMin(t):
        if t[2].lower() == 'pm' and int(t[0]) < 12:
            return (int(t[0]) + 12, int(t[1]))
        else:
            return (int(t[0]), int(t[1]))
    t1, t2 = re.findall(r'\b(\d{1,2}):(\d{2})\s*(AM|PM)\b', section['Time'], flags=re.I)
    return [(DAYS.index(day.lower()),) + getHrMin(t1) + getHrMin(t2) \
                for day in section['Days']]

def categorize(elems, key):
    """Return mapping of `key(e)` -> `list of elems` for e in elems."""
    d = defaultdict(list)
    for e in elems:
        d[key(e)].append(e)
    return d

def planSchedule(classes, badIvals=(), curCRNs=(), verbose=False):
    """
    Return a map of `class` -> `list of sections to take`.

    class := (subCode, num, year, season)

    Sections that take place during intervals in badIvals are not considered.
    Sections that are closed are also not considered, unless their CRN is in
    `curCRNs` (sequence of ints).
    """
    def printV(*args):
        if verbose:
            print ' '.join(str(a) for a in args)

    # Contains lists of mutually exclusive sections - a schedule is made by
    # selecting one item out of each list.
    secClusters = []

    for cls in classes:
        printV('finding sections for', cls)
        sections = getClassSections(*cls)
        printV('done')

        for sec in sections:
            # replace Time and Days with Intervals attribute
            sec['Intervals'] = sectionToIntervals(sec)
            del sec['Time']
            del sec['Days']

            # delete some other stuff so it prints nicer for debugging
            del sec['Detail']
            del sec['Instructor']
            del sec['Location']

            # add class
            sec['Class'] = cls

        tpToSecList = categorize(sections, key=lambda sec: sec['Type'])

        # filter each section list by if closed and if overlap with badIvals
        for tp, secs in tpToSecList.iteritems():
            tpToSecList[tp] = [sec for sec in secs \
                    if not any(overlaps(secInter, badIval) \
                            for secInter in sec['Intervals'] \
                            for badIval in badIvals) \
                        and (int(sec['CRN']) in curCRNs or 'closed' not in sec['Status'])]

        # check for any categories with no sections open
        for tp, secs in tpToSecList.iteritems():
            if not secs:
                raise Exception('No sections available for %s, %s' \
                        % (str(cls), tp))

        secClusters += tpToSecList.values()

    printV('calculating schedule')
    sectionsToTake = utils.oneFromEach(secClusters, lambda sec1, sec2: any(overlaps(i1, i2) for i1 in sec1['Intervals'] for i2 in sec2['Intervals']))
    printV('done')
    printV()

    clsToSections = categorize(sectionsToTake, key=lambda sec: sec['Class'])
    return clsToSections

if __name__ == '__main__':
    import doctest
    doctest.testmod()

##    pprint(getClasses('ECE', 2012, 'fall'))
    classes = (
            ('ECE', 313, 2012, 'fall'),
            ('PHYS', 214, 2012, 'fall'),
            )

    print 'Enter prohibited times in this format:'
    print '     >>> MWF 8:00 9:50 5:00 6:00'
    print '     Hours 8-11 will be interpreted as AM, otherwise PM'
    inp = raw_input('>>> ')
    if inp:
        badIvals = strToIntervals(inp)
    else:
        badIvals = []

    clsToSections = planSchedule(classes, badIvals)

    for cls, secs in clsToSections.iteritems():
        print '*** %s %s' % cls[:2]
        for sec in secs:
            print '  -', sec['Type']
            print '    CRN:', sec['CRN']
            print '    Times:'
            for ival in sec['Intervals']:
                print '      ', reprInterval(ival)
            print
