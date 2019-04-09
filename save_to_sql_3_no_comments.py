import requests
from bs4 import BeautifulSoup
import re
import datetime
from datetime import timedelta
import time
import random
import pprint
import mysql.connector

def formData(input='default'):
    date1 = datetime.date.today()
    date2 = date1 + timedelta(days=60)
    date1 = date1.strftime('%m/%d/%Y')
    date2 = date2.strftime('%m/%d/%Y')
    form_data = {
        'agree' : {
            'ctl00$ctl00$siteMasterHolder$basicBodyHolder$btnAgree' : 'I+Agree'
        },
        'search' : {
            'ctl00$ctl00$siteMasterHolder$basicBodyHolder$btnSubmit' : 'Search'
        },
        'default' : {
            'ctl00$ctl00$siteMasterHolder$basicBodyHolder$txtCaseNumber':'',
            'ctl00$ctl00$siteMasterHolder$basicBodyHolder$txtFirstName':'',
            'ctl00$ctl00$siteMasterHolder$basicBodyHolder$txtLastName':'',
            'ctl00$ctl00$siteMasterHolder$basicBodyHolder$rbNameOption':'rbNameOptionExact',
            'ctl00$ctl00$siteMasterHolder$basicBodyHolder$ddlDOBMonth':'',
            'ctl00$ctl00$siteMasterHolder$basicBodyHolder$ddlDOBDay':'',
            'ctl00$ctl00$siteMasterHolder$basicBodyHolder$txtDOBYear':'',
            'ctl00$ctl00$siteMasterHolder$basicBodyHolder$rbDOBOption':'rbDOBOptionExact',
            'ctl00$ctl00$siteMasterHolder$basicBodyHolder$txtDateFrom': date1,
            'ctl00$ctl00$siteMasterHolder$basicBodyHolder$txtDateTo': date2
        },
        'get courthouse': {
            'ctl00$ctl00$siteMasterHolder$basicBodyHolder$ScriptManager1' : 'ctl00$ctl00$siteMasterHolder$basicBodyHolder$ScriptManager1|ctl00$ctl00$siteMasterHolder$basicBodyHolder$ddlCourthouse',
            '__EVENTTARGET':'ctl00$ctl00$siteMasterHolder$basicBodyHolder$ddlCourthouse',
            '__ASYNCPOST':'true'
        }
    }
    return form_data[input]

def timeDelay(minimum, maximum):
    while True:
        a = random.gammavariate(3, .9)
        if a>=minimum and a<maximum:
            break
    time.sleep(2*a)

def openSession():
    global s
    headers = {
        'Host': 'www.lacourt.org',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'en-US,en;q=0.9'}
    s = requests.Session()
    s.headers.update(headers)

def sendNext(req):
    r = s.prepare_request(req)
    response = s.send(r)
    s.headers.update({'referer': response.url})
    return response

def setup():
    openSession() 
    response, state, soup = getToForm() 
    locations, response = collectLocations(soup)
    return response, locations

def getToForm():
    state = "start"
    soup = None 
    while state != "blank form":
        req = nextRequest(state, soup) 
        timeDelay(1.5, 4)
        response = sendNext(req) 
        state, soup = parseResponse(response) 
    return response, state, soup

def nextRequest(state, soup, **location):
    data = {}
    if state == 'start':
        req = requests.Request('GET', 'http://www.lacourt.org/criminalcalendar/ui/', data={})
    elif state == 'disclaimer prompt':
        req = requests.Request('POST', 'http://www.lacourt.org/criminalcalendar/ui/')
        data.update(formData('agree'))
        data.update(hiddenFormData(soup))
    elif state == 'blank form':
        req = requests.Request('POST', 'http://www.lacourt.org/criminalcalendar/ui/')
        data.update(formData('default'))
        data.update(formData('get courthouse'))
        data.update({'ctl00$ctl00$siteMasterHolder$basicBodyHolder$ddlCourthouse': location['courthouse']})
        data.update(hiddenFormData(soup))
    elif state == 'new form':
        req = requests.Request('POST', 'http://www.lacourt.org/criminalcalendar/ui/Index.aspx')
        data.update(formData('default'))
        data.update(formData('get courthouse'))
        data.update({'ctl00$ctl00$siteMasterHolder$basicBodyHolder$ddlCourthouse': location['courthouse']})
        data.update(hiddenFormData(soup))
    elif state == 'panel update':
        req = requests.Request('POST', 'http://www.lacourt.org/criminalcalendar/ui/')
        data.update(formData('default'))
        data.update({'ctl00$ctl00$siteMasterHolder$basicBodyHolder$ddlDepartment' : location['department']})
        data.update({'ctl00$ctl00$siteMasterHolder$basicBodyHolder$ddlCourthouse': location['courthouse']})
        data.update(formData('search'))
        data.update(hiddenFormData(soup)) 
    elif state == 'new panel update':
        req = requests.Request('POST', 'http://www.lacourt.org/criminalcalendar/ui/Index.aspx')
        data.update(formData('default'))
        data.update({'ctl00$ctl00$siteMasterHolder$basicBodyHolder$ddlDepartment' : location['department']})
        data.update({'ctl00$ctl00$siteMasterHolder$basicBodyHolder$ddlCourthouse': location['courthouse']})
        data.update(formData('search'))
        data.update(hiddenFormData(soup)) 
    elif state == 'redirect':
        url = req.headers['Host'] + re.search('pageRedirect\|\|([^|]*)\|', soup.text).group(1).replace('%2f', '/')
        req = requests.Request('GET', url)
    elif state == 'results':
        req = requests.Request('GET', 'http://www.lacourt.org/criminalcalendar/ui/popupCalendarList.aspx')
        data.update(hiddenFormData(soup))
    elif state == 'completed department':
        req = requests.Request('GET', 'http://www.lacourt.org/criminalcalendar/ui/Index.aspx')
        req.headers.update({'referer': 'http://www.lacourt.org/criminalcalendar/ui/CalendarList.aspx'})
    req.data = data
    return req

def hiddenFormData(input):
    hidden_data = {}
    if isinstance(input, BeautifulSoup):
        results = input.find_all(attrs = {'type': 'hidden'})
        for result in results:
            hidden_data[result['name']] = result['value']
    elif isinstance(input, requests.models.Response):
        results = re.findall('(__.+?)\|([^|]*)\|', input.text)
        for result in results:
            hidden_data[result[0]] = result[1]
    return hidden_data

def parseResponse(response):
    if 'html' in response.text:
        soup = BeautifulSoup(response.text, "html.parser")
        if soup.find('input', id="siteMasterHolder_basicBodyHolder_btnAgree"):
            state = 'disclaimer prompt'
        elif soup.title.get_text(strip=True) == 'Criminal Case Calendar - Online Services - LA Court' and not soup.find('table', id="siteMasterHolder_basicBodyHolder_CalendarSearchResultList_gvResults") and response.url == 'http://www.lacourt.org/criminalcalendar/ui/':
            state = 'blank form'
        elif soup.title.get_text(strip=True) == 'Criminal Case Calendar - Online Services - LA Court' and not soup.find('table', id="siteMasterHolder_basicBodyHolder_CalendarSearchResultList_gvResults") and response.url == 'http://www.lacourt.org/criminalcalendar/ui/Index.aspx':
            state = 'new form'
        elif soup.title.get_text(strip=True) == 'Criminal Case Calendar - Online Services - LA Court' and soup.find('table', id="siteMasterHolder_basicBodyHolder_CalendarSearchResultList_gvResults"):
            state = 'results'
        elif soup.title.get_text(strip=True) == 'Criminal Case Calendar Search Result':
            state = 'full results'
    elif 'updatePanel' in response.text and response.url == 'http://www.lacourt.org/criminalcalendar/ui/':
        state = 'panel update'
        soup = response
    elif 'updatePanel' in response.text and response.url == 'http://www.lacourt.org/criminalcalendar/ui/Index.aspx':
        state = 'new panel update'
        soup = response
    elif 'pageRedirect' in response.text:
        state = 'redirect'
        soup = response
    return state, soup

def collectLocations(soup):
    locations = {}
    for court in soup.find_all('select', id="siteMasterHolder_basicBodyHolder_ddlCourthouse")[0].find_all('option'):
        if court.text != '':
            locations.update({court.text : []})
    print('building location dict:')
    for court in locations:
        print(court)
        req = nextRequest('blank form', soup, courthouse=court)
        timeDelay(1, 2)
        response = sendNext(req)
        state_discard, soup = parseResponse(response)
        results = re.findall('option value=\".+\"\>(.+)\</option', soup.text) 
        locations[court] = results
    return locations, soup

def locationLoop(locations, soup):
    state = 'blank form'
    print('scraping:')
    for court, departments in locations.items():
            print(court)
            for department in departments:
                print(department)
                while state != 'full results':
                    print(state)
                    req = nextRequest(state, soup, courthouse=court, department=department)
                    timeDelay(1.5, 4)
                    response = sendNext(req)
                    state, soup = parseResponse(response)
                dept_calendar = extractResults(soup)
                commitResults(dept_calendar)
                state = 'completed department'
    saveTable()

def extractResults(soup):
    results = soup.find_all('tr', ['toggle1', 'toggle2'])
    table = []
    for i in range(len(results)):
        table.append([])
        a = results[i].find_all('td') 
        for col in a:
            table[i].append(col.get_text())
    return table

def commitResults(dept_calendar):
    insert_raw = (
    "INSERT INTO calendar_data (district, case_no, defendant_no, defendant, arrested, courthouse, department, date, time, type)"
    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
    )
    cnx = mysql.connector.connect(user='root', password='password', database='criminal_case_calendar')
    cur = cnx.cursor()
    cur.executemany(insert_raw, dept_calendar)
    cnx.commit()
    cur.close()
    cnx.close()

def saveTable():
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    copy_raw = ("CREATE TABLE %s_calendar SELECT * FROM calendar_data" % timestamp)
    cnx = mysql.connector.connect(user='root', password='password', database='criminal_case_calendar')
    cur = cnx.cursor()
    cur.execute(copy_raw)
    clear_raw = ("TRUNCATE TABLE calendar_data;")
    cnx = mysql.connector.connect(user='root', password='password', database='criminal_case_calendar')
    cur = cnx.cursor()
    cur.execute(clear_raw)
    cnx.commit()
    cur.close()
    cnx.close()
    print("Saved to table %s_calendar" % timestamp)