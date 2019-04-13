import requests
from bs4 import BeautifulSoup
import re
import datetime
from datetime import timedelta
import time
import random
import pprint
import mysql.connector

def formData(input='default', *subcase_info):
#    print("formData")
    if subcase_info != ():
        subcase_info = subcase_info[0]
        case_no = subcase_info[0]
        defe= subcase_info[1]
        loc = subcase_info[2]
        crt = subcase_info[3].replace(" ", "+")
    else :
        [case_no, defe, loc, crt] = ['', '', '', '']
#    print(subcase_info)
#    print(crt)
#    print([case_no, defe, loc, crt])
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
            'csn': case_no,
            'loc': loc,
            'def': defe,
            'crt': crt
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

def nextRequest(state, soup, *subcase_info):
    if subcase_info != ():
        subcase_info = subcase_info[0]
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
        data.update(formData('search', subcase_info))
        data.update(hiddenFormData(soup))
# when locationLoop begins, the raw response object is passed to nextRequest as soup
    elif state == 'new form':
# enter courthouse
        req = requests.Request('POST', 'http://www.lacourt.org/criminalcasesummary/ui/index.aspx')
        data.update(formData('search', subcase_info))
        data.update(hiddenFormData(soup))
# when locationLoop begins, the raw response object is passed to nextRequest as soup
    elif state == 'selection':
# select department & submit
#req = requests.Request('POST', 'http://www.lacourt.org/criminalcasesummary/ui/Selection.aspx')
# select courthouse or defendant and activate loop/loop tracking
        req = requests.Request('POST', 'http://www.lacourt.org/criminalcasesummary/ui/Selection.aspx')
        req.headers.update({'referer': 'http://www.lacourt.org/criminalcasesummary/ui/Selection.aspx'})
#        data.update(formData('subcase', subcase_info))
        data.update(hiddenFormData(soup)) 
        data.update(formData('subcase', subcase_info))
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
        req = requests.Request('GET', 'http://www.lacourt.org/criminalcasesummary/ui/index.aspx')
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
        elif soup.find('span', id="PlsSelectFromTheList"):
# or soup.find('input', id="siteMasterHolder_basicBodyHolder_caseNumber")
            state = 'selection'
        elif soup.title.get_text(strip=True) == 'LASC - Criminal Case Summary':
            state = 'results'
        elif soup.title.get_text(strip=True) == 'Criminal Case Summary':
            state = 'full results'
        elif soup.find('span', id="siteMasterHolder_basicBodyHolder_lbMsg").text == "Case Was not found.":
            state = "error"
        else:
            state = 'new form'
    elif 'updatePanel' in response.text:
        state = 'panel update'
        soup = response
    elif 'Object moved to' in response.text:
# "object moved to" ?
        state = 'redirect'
        soup = response
    else:
        state="error"
# error - not found, 
# call getToForm, re-evaluate locations, set locations equal to locations not already committed to DB
#<p class="txtHeader">An Error Has Occured.</p>\r\n    <p class="txtBodySamll">\r\n        An unexpected error occured on our website. The website administrator has been notified.\r\n    </p>
    return state, soup

def eachCaseLoop(state, soup, subcase_info):
    state = 'new form'
    while (state != 'full results' and state!= "error"):
#will this always terminate at selection. even if only one case result?
        req = nextRequest(state, soup, subcase_info)
        timeDelay(.5, 1.5)
        print(state)
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
    curA = cnx.cursor()
    subcase_qry = ("SELECT DISTINCT csn, def, loc, crt FROM subcases where concat(loc, csn, '-', def) not in (select case_numb from case_info) and crt not like '%;%'")
    curA.execute(subcase_qry)
    subc = curA.fetchone()
    while subc is not None:
        subcase_info = [subc[0], subc[1], subc[2], subc[3]]
        print("caseLoop")
        print(subcase_info)
        response, state, soup = eachCaseLoop(state, soup, subcase_info)
        subcase_no = subcase_info[2]+subcase_info[0]+'-'+subcase_info[1]
        if state == 'full results':
            case_info = extractCaseInfo(subcase_no, soup)
            saveResult(cnx2, response, case_info)
        else:
            print('error')
            saveResult(cnx2, response, (subcase_no, '', '', '', '', '', ''))
#        print(state)
        subc = curA.fetchone()
    cnx.commit()
    cnx.close()
    cnx2.close()

def extractCaseInfo(subcase_no, soup):
#from 'full result'
    if subcase_no == soup.find('div', id="caseNumb").text:
        table = [soup.find('div', id="caseNumb").text]
        results = soup.find('table',  id="FillChargeInfo_tabCaseList")
        if results is not None:
            results = results.find_all('td')
            for result in results:
                table.append(result.text)
            out = (table[0], table[1], table[2], table[3], table[4], table[5], table[6]) 
        else:
            out = (table[0], '', '', '', '', '', '')
    else:
        out = (subcase_no, '', '', '', '', '', '')
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



