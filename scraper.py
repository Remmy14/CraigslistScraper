#!/usr/bin/python3.6

import requests
from bs4 import BeautifulSoup as bs4
import logging
import gmail
import time
from random import randint
import sys

postings = []
FORMAT = '%(asctime)s.%(msecs)03d [%(process)d] [%(levelname)s] - %(message)s'
logging.basicConfig(format=FORMAT, datefmt='%Y-%m-%d %H:%M:%S', filename='scraper.log', filemode='a+', level=10)
requests.packages.urllib3.disable_warnings()
logging.debug("Scraper started.")

# Get our list of postings from the last time we shut down
existing_item_list_file = open("list_file.txt", 'r')
postings = existing_item_list_file.read().splitlines()
existing_item_list_file.close()

def get_price(text):
	prices = text.find_all('span', attrs={'class':'result-price'})
	if len(prices) > 0:
		return prices[0].get_text()
	else:
		logging.critical("Failed to get a price")
		return 'None'

def get_location(text):
	locations = text.find_all('span', attrs={'class':'result-hood'})
	if len(locations) == 0:
		locations = text.find_all('span', attrs={'class':'nearby'})

	if len(locations) == 0:
		# We tried our best. Let's get the fuck outta dodge
		logging.critical("Failed to get a location")
		return 'None.'
	else:
		return locations[0].get_text()

def get_post_name(text):
	names = text.find_all('a', attrs={'class':'result-title hdrlnk'})
	try:
		return names[0].get_text()
	except:
		logging.critical("Failed to get a name")
		return None

def get_post_link(text):
	try:
		return text.a['href']
	except:
		logging.critical("Failed to get a link")
		return None

def get_post_time(text):
	try:
		return text.time['title']
	except:
		logging.critical("Failed to get a post time")
		return None

while True:
	city = "dayton"
	url = ".craigslist.org/search/sss/?query="

	thing_list_file = open('item_list_file.txt', 'r')
	thing_list = thing_list_file.readlines()
	thing_list_file.close()

	for thing in thing_list:
		query = "https://" + city + url + thing.strip()

		try:
			rsp = requests.get(query, timeout=20)
			success = True
		except:
			logging.debug("We had a timeout in getting the request. Try again in a bit.")
			success = False

		if success:
			html = bs4(rsp.text, 'html.parser')
			new_items = html.find_all('li', attrs={'class':'result-row'})
			number_of_items = len(new_items)
			number_of_new_items = 0

			for item in new_items:
				pid = item['data-pid']
				if pid not in postings:
					# We have a unique new listing and need to email out
					number_of_new_items = number_of_new_items + 1
					price = get_price(item)
					local = get_location(item)
					name = get_post_name(item)
					link = get_post_link(item)
					post_time = get_post_time(item)

					body = "Name: {0}\nPrice: {1}\nLocation: {2}\nPosted: {3}\nLink: {4}".format(name, price, local, post_time, link)

					# Read in uname/pword here so that it's not in memory
					creds_file = open('arcf/.creds_file.txt', 'r')
					uname = creds_file.readline().strip()
					pword = creds_file.readline().strip()
					creds_file.close()
					gm = gmail.GMail(uname, pword)
					uname = None
					pword = None
					gm.connect()

					try:
						msg = gmail.Message('New {} Found on Craigslist'.format(thing.strip().upper()), to = 'alex.remillard@gmail.com', text=body)
						gm.send(msg)
						postings.append(pid)

						# Update our list
						existing_item_list_file = open("list_file.txt", 'w')
						for p in postings:
							existing_item_list_file.write(str(p) + '\n')
						existing_item_list_file.close()
					except:
						logging.debug("Something went wrong for posting {}".format(pid))
						pass


			logging.info("For item {0} we found {1} items, {2} of which are new".format(thing.strip(), number_of_items, number_of_new_items))

		# Sleep for between 1 and 3 minutes
		time.sleep(randint(60, 180))
