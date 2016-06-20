#!/bin/env python

import mechanize
import cookielib
from bs4 import BeautifulSoup
import html2text
import urllib2
import re
import datetime
import cx_Oracle

def sendPostBaldenini(url, payload):
	pl_len=len(payload)
	headers = {
	'Host': 'baldenini.by',
	'Connection': 'keep-alive',
	'Content-Length': '%s'%pl_len,
	'Accept': 'application/json, text/javascript, */*; q=0.01',
	'Origin': 'http://baldenini.by',
	'X-Requested-With': 'XMLHttpRequest',
	'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.87 Safari/537.36',
	'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
	'Referer': 'http://baldenini.by/company_orders',
	'Accept-Encoding': 'gzip, deflate',
	'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4,be;q=0.2,fr;q=0.2'
	}
	post=urllib2.Request(url, payload, headers)
	return post
url  = 'http://baldenini.by/login' #login page
url0 = 'http://baldenini.by/company_orders'
url1 = 'http://baldenini.by/get_group_order_block' #company order
url2 = 'http://baldenini.by/get_order_block' #pesonal order

# Browser
br = mechanize.Browser()

# Cookie Jar
cj = cookielib.LWPCookieJar()
br.set_cookiejar(cj)

# Browser options
br.set_handle_equiv(True)
br.set_handle_redirect(True)
br.set_handle_referer(True)
br.set_handle_robots(False)
br.set_handle_refresh(mechanize._http.HTTPRefreshProcessor(), max_time=1)
br.addheaders = [('User-agent', 'Chrome')]

# Login to the site
br.open(url)
br.select_form(nr=0)
br.form['userName'] = '#######@gmail.com'
br.form['password'] = '#######'
br.submit()

# Navigate to page containing company orders and read their ids and dates
soup=BeautifulSoup(br.open(url0).read(), "lxml")
ids=soup.tbody.find_all("div", class_="id")
ids=soup.tbody.find_all("div", class_="id")
dates=soup.tbody.find_all("div", class_="date")

# Align dates and ids, get order contents and orders down the hierarchy
im=len(ids)
i=0
currdate=datetime.datetime.today().strftime('%d.%m.%Y 13:00')
personal_orders_stg=open('/usr/upload/personal_orders_stg.txt','w')
while (i<im):
	res=ids[i]
	order_id=res.text
	date=dates[i]
	order_date=date.text
	if order_date!=currdate: 										#DELTA LOAD! COMMENT THIS LINE FOR FULL LOAD
		break 														#DELTA LOAD! COMMENT THIS LINE FOR FULL LOAD
	payload = 'order_id=%s'%order_id
	post=sendPostBaldenini(url1, payload) 
	order=BeautifulSoup(br.open(post).read().decode('unicode-escape'), "lxml")
	order_li=order.find_all("div", class_="aclient_item_info")
	personal_order_ids=order.find_all("a", class_="aclient_item", target="_blank")
	nm=len(order_li)
	n=0
	m=0
	while n<nm:
		#for each company order, get personal orders id list
 		po=personal_order_ids[m].get('href')
 		po_id=po[po.index('#')+1:]
 		payload = 'order_id=%s'%po_id
 		post=sendPostBaldenini(url2, payload)
 		order=BeautifulSoup(br.open(post).read().decode('unicode-escape'), "lxml")
 		personal_order_li_dish=order.find_all("div", class_="news_title cl_order")
 		personal_order_li_price=order.find_all("div", class_="event_dish_calc others ng_d_item")
		km=len(personal_order_li_dish)
		k=0
		while k<km:
			#for each personal order, get list of dishes and write them to file
			personal_order_li_price_clean=personal_order_li_price[k].text.replace('\n','').replace(' ','')
			regex = r'[(].+?[)]'
			personal_order_li_price_clean=re.sub(regex, '',personal_order_li_price_clean)
			personal_orders_stg_line='%s; %s; %s; %s; %s; %s; %s; %s\n'%(order_id, po_id, order_date, order_li[n].text, order_li[n+1].text, order_li[n+2].text, personal_order_li_dish[k].text, personal_order_li_price_clean)
			personal_orders_stg.write(personal_orders_stg_line.encode('utf-8'))
	 		k+=1		 		
	 	n+=3
	 	m+=1


	i+=1
	
personal_orders_stg.close()

conn = cx_Oracle.Connection("POWERLUNCH/#######@//localhost:1521/#######")
curs = conn.cursor()
curs.callproc("dbms_output.enable")
curs.callproc("ORDERS_LOAD")
 
statusVar = curs.var(cx_Oracle.NUMBER)
lineVar = curs.var(cx_Oracle.STRING)
while True:
  curs.callproc("dbms_output.get_line", (lineVar, statusVar))
  if statusVar.getvalue() != 0:
    break
  print lineVar.getvalue()

conn.cursor().close