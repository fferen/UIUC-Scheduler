#!/usr/bin/env python
import logging
import json

import webapp2
import courses
import misc

DEBUG = False

subCodeToClasses = None
year = None
season = None

if DEBUG:
    try:
        logging.info('loading classes')
        subCodeToClasses = json.loads(open('classes').read())
        logging.info('done')
        year = 2012
        season = 'fall'
    except IOError:
        pass

def parseJSTime(t):
    time, ampm = t.split()
    hr, m = time.split(':')
    hr, m = int(hr), int(m)
    if ampm == 'PM' and hr < 12:
        hr += 12
    return (hr, m)

def parseJSInterval(times, dayBools):
    days = [i for i in xrange(len(dayBools)) if dayBools[i]]
    startTime, endTime = [parseJSTime(t) for t in times]

    return [(day,) + startTime + endTime for day in days]

class Update(webapp2.RequestHandler):
    def get(self):
        global subCodeToClasses
        global year
        global season

        year, season = courses.getCurYearSeason()
        subCodes = courses.getSubCodes(year, season)
        allClasses = []
        for code in subCodes:
            allClasses += courses.getClasses(code, year, season)

        subCodeToClasses = courses.categorize(allClasses, lambda cls: cls['Subject Code'])
        if DEBUG:
            self.response.out.write(json.dumps(subCodeToClasses))

class MainPage(webapp2.RequestHandler):
    def get(self):
        self.response.out.write(open('index.html').read().replace('__subCodeToClasses__', json.dumps(subCodeToClasses)))

class Solve(webapp2.RequestHandler):
    def post(self):
        # array of time strings: "08:00 AM"
        bannedTimes = json.loads(self.request.get('bannedTimes'))
        # array of all bannedDays checkboxes (booleans)
        bannedDays = json.loads(self.request.get('bannedDays'))

        badIvals = []
        # each 2 time strings corresponds to 5 bannedDays checkboxes
        for dayBools, times in zip(misc.iterGroups(bannedDays, 5), misc.iterGroups(bannedTimes, 2)):
            badIvals += parseJSInterval(times, dayBools)

        subCodes = json.loads(self.request.get('subCodes'))
        nums = json.loads(self.request.get('nums'))
        curCRNs = json.loads(self.request.get('curCRNs'))

        classes = [t + (year, season) for t in zip(subCodes, nums)]

        try:
            clsToSections = courses.planSchedule(classes, badIvals, curCRNs)
        except:
            self.response.out.write(json.dumps({}))
        else:
            for cls, sections in clsToSections.items():
                clsToSections[cls[0] + ' ' + str(cls[1])] = sections
                del clsToSections[cls]

                for sec in sections:
                    sec['Intervals'] = [courses.reprInterval(i) for i in sec['Intervals']]

            self.response.out.write(json.dumps(clsToSections))

##class Complete(webapp2.RequestHandler):
##    def get(self):
##        s = self.request.get('s')
##        words = [w.lower() for w in s.split()]
##
##        completions = []
##        for cls in subCodeToClasses:
##            qual = 0
##            for w in words:
##                if w == cls['Subject Code']:
##                    qual += 1
##                elif w == cls['Number']:
##                    qual += 1
##                elif w in cls['Course Title']:
##                    qual += 0.5
##            if qual:
##                completions.append((qual, cls))
##
##        completions.sort(reverse=True)
##        self.response.out.write(json.dumps(completions))

class Sections(webapp2.RequestHandler):
    def get(self):
        subCode = self.request.get('subCode')
        num = int(self.request.get('num'))
        self.response.out.write(json.dumps(courses.getClassSections(subCode, num, year, season)))

app = webapp2.WSGIApplication([
            ('/', MainPage),
            ('/solve', Solve),
            ('/update', Update),
            ('/sections', Sections)
##            ('/complete', Complete)
            ], debug=DEBUG)
