issue: multiple courthouses/defendants:
    all subcases are displayed on selection page - do not have to click through defendant and then click through courthouse
    defendants have ID no.s
    count # is sequential across defendants e.g. defendant 1 has counts 1 & 2, defendant 2 has counts 3-5
	selection prompt:
	http://www.lacourt.org/criminalcasesummary/ui/Selection.aspx
	returns:
	http://www.lacourt.org/criminalcasesummary/ui/Selection.aspx
	if Selection.aspx, make a selection, or loop through the same case no again and choose other selection
issue: many case no's to look up one at a time and website appears to be slow
	-first reduce to unique case no's instead of iterating over all records in calendar_data
	-check case summary DB for case no and don't query/update every case no every time - likely not change frequently

open cursor to fetch case_no's
	select distinct case no's
	start with case no's not already in case summary DB
	proceed by soonest hearing date

case summary:
http://www.lacourt.org/criminalcasesummary/ui/
*agree
http://www.lacourt.org/criminalcasesummary/ui/
*enter case no
*choose courthouse/defendant
*submit search
*Object moved to <a href="/criminalcasesummary/ui/Selection.aspx"
*Object moved to <a href="/criminalcasesummary/ui/InfoPanel.aspx"
http://www.lacourt.org/criminalcasesummary/ui/InfoPanel.aspx
*print results
*extract tables - case info, events, bail (if available), sentencing (if avail)

new search:
http://www.lacourt.org/criminalcasesummary/ui/index.aspx

import requests
from bs4 import BeautifulSoup
import re
import datetime
from datetime import timedelta
import time
import random
import pprint
import mysql.connector

def formData(input='default', *case_no):
    
    form_data = {
        'agree' : {
            'ctl00$ctl00$siteMasterHolder$basicCategoryHolder$ddlLanguages' : 'en-us',
            'ctl00$ctl00$siteMasterHolder$basicBodyHolder$btnAgree' : 'I+Agree'
        },
        'search' : {
            'ctl00$ctl00$siteMasterHolder$basicCategoryHolder$ddlLanguages' : 'en-us',
            'ctl00$ctl00$siteMasterHolder$basicBodyHolder$caseNumber' : case_no,
            'ctl00$ctl00$siteMasterHolder$basicBodyHolder$loc' : '',
            'subcase' : 'Submit'
        },
        'subcase' : {
            'ctl00$ctl00$siteMasterHolder$basicCategoryHolder$ddlLanguages' : 'en-us',
            'csn':'VA148764',
            'loc':'LAM',
            'def':'01',
            'crt':'Metropolitan Courthouse'
        }
        }
    return form_data[input]

def timeDelay(minimum, maximum):
    while True:
        a = random.gammavariate(3, .9)
        if a>=minimum and a<maximum:
            break
    time.sleep(a)

def openSession():
    global s
    headers = {
        'Host': 'www.lacourt.org',
        'Connection': 'keep-alive',
        'Cache-Control': 'max-age=0',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36',
        'DNT' : '1',
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

def getCaseNos():
    return ["VA148764"]

def setup():
    openSession() 
    response, state, soup = getToForm()
    return soup, state

def getToForm():
    state = "start"
    soup = None 
    while state != "blank form":
        req = nextRequest(state, soup) 
        timeDelay(1.5, 4)
        response = sendNext(req) 
        state, soup = parseResponse(response) 
    return response, state, soup

def nextRequest(state, soup, *case_no):
    data = {}
    if state == 'start':
        req = requests.Request('GET', 'http://www.lacourt.org/criminalcasesummary/ui/', data={})
    elif state == 'disclaimer prompt':
#agree
        req = requests.Request('POST', 'http://www.lacourt.org/criminalcasesummary/ui/')
        data.update(formData('agree'))
        data.update(hiddenFormData(soup))
    elif state == 'blank form':
# enter courthouse
        req = requests.Request('POST', 'http://www.lacourt.org/criminalcasesummary/ui/')
        data.update(formData('search', case_no))
        data.update(hiddenFormData(soup))
# when locationLoop begins, the raw response object is passed to nextRequest as soup
    elif state == 'new form':
# enter courthouse
        req = requests.Request('POST', 'http://www.lacourt.org/criminalcasesummary/ui/Index.aspx')
        data.update(formData('search', case_no))
        data.update(hiddenFormData(soup))
# when locationLoop begins, the raw response object is passed to nextRequest as soup
    elif state == 'selection':
# select department & submit
#req = requests.Request('POST', 'http://www.lacourt.org/criminalcasesummary/ui/Selection.aspx')
# select courthouse or defendant and activate loop/loop tracking
        req = requests.Request('GET', 'http://www.lacourt.org/criminalcasesummary/ui/Index.aspx')
        req.headers.update({'referer': 'http://www.lacourt.org/criminalcasesummary/ui/Selection.aspx'})
        data.update(hiddenFormData(soup)) 
# in this case the raw response object is passed to nextRequest as soup
    elif state == 'redirect':
# GET result page
        url = req.headers['Host'] + re.search('pageRedirect\|\|([^|]*)\|', soup.text).group(1).replace('%2f', '/')
        req = requests.Request('GET', url)
# redirect never actually seems to come up, but if it does, the raw response object is passed as soup
    elif state == 'results':
# print all
        req = requests.Request('GET', 'http://www.lacourt.org/criminalcasesummary/ui/Popup.aspx')
        data.update(hiddenFormData(soup))
    elif state == 'full results':
# extract results & commit to database
        req = requests.Request('GET', 'http://www.lacourt.org/criminalcasesummary/ui/Index.aspx')
        req.headers.update({'referer': 'http://www.lacourt.org/criminalcasesummary/ui/Selection.aspx'})
    elif state == 'completed case_no':
        pass
    req.data = data
    return req

def parseResponse(response):
    if 'html' in response.text:
        soup = BeautifulSoup(response.text, "html.parser")
        if soup.find('input', id="siteMasterHolder_basicBodyHolder_btnAgree"):
            state = 'disclaimer prompt'
        elif soup.title.get_text(strip=True) == 'Criminal Case Summary - Online Services - LA Court' and soup.find('div', id="siteMasterHolder_basicBodyHolder_pnlSearch") and response.url == 'http://www.lacourt.org/criminalcasesummary/ui/':
            state = 'blank form'
        elif soup.title.get_text(strip=True) == 'Criminal Case Summary - Online Services - LA Court' and soup.find('div', id="siteMasterHolder_basicBodyHolder_pnlSearch") and response.url == 'http://www.lacourt.org/criminalcasesummary/ui/Index.aspx':
            state = 'new form' 
        elif soup.find('span', id="PlsSelectFromTheList") or soup.find('input', id="siteMasterHolder_basicBodyHolder_caseNumber"):
            state = 'selection'
        elif soup.title.get_text(strip=True) == 'LASC - Criminal Case Summary':
            state = 'results'
        elif soup.title.get_text(strip=True) == 'Criminal Case Summary':
            state = 'full results'
        else:
            state = 'start'
    elif 'updatePanel' in response.text:
        state = 'panel update'
        soup = response
    elif 'Object moved to' in response.text:
# "object moved to" ?
        state = 'redirect'
        soup = response
    else:
        pass
# error - not found, 
# call getToForm, re-evaluate locations, set locations equal to locations not already committed to DB
#<p class="txtHeader">An Error Has Occured.</p>\r\n    <p class="txtBodySamll">\r\n        An unexpected error occured on our website. The website administrator has been notified.\r\n    </p>
    return state, soup

def caseWorker(state, case_no, soup):
    if state == 'blank form' or state == 'new form':
        req = nextRequest(state, soup, case_no)
        timeDelay(1.5, 4)
        response = sendNext(req)
        state, soup = parseResponse(response)
        if state == 'results':
            subcases = []
# create subcase table
        elif state == 'selection':
            subcases = re.findall('transferInfo[^\)]*\'(.*)\',\'(.*)\',\'(.*)\',\'(.*)\'', response.text)
# create subcase table
        else:
            print('caseWorker had trouble with %s' % case_no)
            subcases = []
    else:
        print('caseWorker needs to start at the search form')
        subcases = []
    return state, soup, subcases


def eachCaseLoop(state, soup, case_no):
    state = 'new form'
    while (state != 'full results' and state != 'selection'):
#will this always terminate at selection. even if only one case result?
        req = nextRequest(state, soup, case_no)
        timeDelay(.5, 1.5)
        response = sendNext(req)
        state, soup = parseResponse(response)
    return response, state, soup

#need to clean up subcase table - some duplicates entered 
# also need to clean up compound code section entries
### ideas
# rank cities by municipal code violation
# most common code violations
# statutes most often invoked
# proportions of pleas & dispositions, perhaps by location or code section
# oddball code violations
# jury trials
# cases with most defendants
# defendants with most charges
# 
###
def caseLoop():
    soup, state = setup()
    print('scraping:')
    cnx = mysql.connector.connect(user='root', password='password', database='criminal_case_calendar')
    cnx2 = mysql.connector.connect(user='root', password='password', database='criminal_case_calendar')
    cnx3 = mysql.connector.connect(user='root', password='password', database='criminal_case_calendar')
    curA = cnx.cursor()
    case_qry = ("""SELECT DISTINCT case_no FROM 2019_03_30_18_26_29_calendar 
    LEFT JOIN case_info
    ON 2019_03_30_18_26_29_calendar.case_no = case_info.csn 
    LEFT JOIN subcases
    ON 2019_03_30_18_26_29_calendar.case_no = subcases.csn
    WHERE case_info.csn IS NULL AND subcases.csn IS NULL""")
    curA.execute(case_qry)
    case_no = curA.fetchone()
    while case_no is not None:
        print(case_no[0])
        response, state, soup = eachCaseLoop(state, soup, case_no[0])
        if state == 'full results':
            case_info = extractCaseInfo(soup)
            saveResult(cnx2, response, case_info)
        elif state == 'selection':
            subcases = extractSubcases(response)
            saveSubcases(cnx3, subcases)
        else:
            print('error')
            pass
        print(state)
        case_no = curA.fetchone()
    cnx.commit()
    cnx.close()
    cnx2.close()
    cnx3.close()

def extractChargeInfo(soup):
#from 'result' state, not 'full result'
    results = soup.find('table',  id="FillChargeInfo_tabCaseList")
    if results is not None:
        results = results.find_all('td')
        i=0
        table = []
        while i <= len(results)/6:
            table.append((soup.find('div', id="caseNumb").text, results[i].text, results[i+1].text, results[i+2].text, results[i+3].text, results[i+4].text, results[i+5].text))
            i+=1
    else:
        table = (soup.find('div', id="caseNumb").text, '', '', '', '', '', '')
    return table

extractChargeInfo(soup)

def extractCaseInfo(soup):
#from 'full result'
    table = [soup.find('div', id="caseNumb").text]
    results = soup.find('table',  id="FillChargeInfo_tabCaseList")
    if results is not None:
        results = results.find_all('td')
        for result in results:
            table.append(result.text)
        out = (table[0], table[1], table[2], table[3], table[4], table[5], table[6]) 
    else:
        out = (table[0], '', '', '', '', '', '')
    return out 

def saveResult(cnx2, response, case_info):
    curB = cnx2.cursor()
    curC = cnx2.cursor()
    insert_result = (
    "INSERT INTO html (case_numb, result_html)"
    "VALUES (%s, %s)"
    )
    data = (case_info[0], response.text)
    curB.execute(insert_result, data)
    cnx2.commit()
    insert_case_info= (
    "INSERT INTO case_info (case_numb, def, code_sect, statute, plea, disposition, date)"
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
    )
    curC.execute(insert_case_info, case_info)
    cnx2.commit()


def extractSubcases(response):
    return re.findall('transferInfo[^\)]*\'(.*)\',\'(.*)\',\'(.*)\',\'(.*)\'', response.text)


def saveSubcases(cnx3, subcases):
    curD = cnx3.cursor()
    insert_subcase = (
    "INSERT INTO subcases (csn, loc, def, crt)"
    "VALUES (%s, %s, %s, %s)"
    )
    curD.executemany(insert_subcase, subcases)
    cnx3.commit()



