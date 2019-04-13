import requests
from bs4 import BeautifulSoup
import re
import datetime
from datetime import timedelta
import time
import random
import pprint
import mysql.connector

def countLoop():
    cnx = mysql.connector.connect(user='root', password='password', database='criminal_case_calendar')
    cnx2 = mysql.connector.connect(user='root', password='password', database='criminal_case_calendar')
    curA = cnx.cursor()
    subcase_qry = ("SELECT * FROM html")
    curA.execute(subcase_qry)
    case = curA.fetchone()
    while case is not None:
        print(case[1])
        soup = BeautifulSoup(case[2], "html.parser")
        charges = extractChargeInfo(case[1], soup)
        saveCounts(cnx2, charges)
        case = curA.fetchone()
    cnx.commit()
    cnx.close()
    cnx2.close()

def extractChargeInfo(subcase_no, soup):
    results = soup.find('table',  id="FillChargeInfo_tabCaseList")
    if results is not None:
        results = results.find_all('td')
        i=0
        table = []
        while i < len(results):
            table.append((soup.find('div', id="caseNumb").text, results[i].text, results[i+1].text, results[i+2].text, results[i+3].text, results[i+4].text, results[i+5].text))
            i+=6
    else:
        if soup.find('div', id="caseNumb") is not None:
            table = [(soup.find('div', id="caseNumb").text, 'NA', 'NA', 'NA', 'NA', 'NA', 'NA')]
        else:
            table = [(subcase_no, 'NA', 'NA', 'NA', 'NA', 'NA', 'NA')]
    return table

def saveCounts(cnx2, charges):
    curB = cnx2.cursor()
    insert_result = (
    "INSERT IGNORE INTO all_counts (case_numb, count, code_sect, statute, plea, disposition, date)"
    "VALUES (%s, %s, %s, %s, %s, %s, %s)"
    )
    curB.executemany(insert_result, charges)
    cnx2.commit()
    curB.close()