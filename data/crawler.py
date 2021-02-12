# coding=utf-8
import requests
from bs4 import BeautifulSoup
import sys
import random
import json
import math
import os
from queue import Queue
from os.path import getsize
import threading

def delete_database():
    filenames = ["document_data.json","inverted_index.json","norms.json"]
    for file in filenames:
        if os.path.isfile(file):
            os.remove(file)
    print("Deleted old files\n")

# gets a text and formats it
def process_text(text):
    # make all letters lowercase
    text = text.lower()

    # removing the below letters from all documents
    delete = [',', '.', '!', '"', '(', ')', ';', ':', '?', '<', '>', '[', ']', '{', '}', '/', '\\', '\'', '-', '_', '`',
              '~', '+', '*', '=', '@', '#', '$', '%', '^', '&', '\n', '\r']
    for char in delete:
        text = text.replace(char, " ")

    text = text.replace('\n', " ")
    # replace letter below (for greek documents)
    old_letter = ["Ά", "Έ", "Ή", "Ί", "Ό", "Ύ", "Ώ", "ά", "έ", "ή", "ί", "ό", "ύ", "ώ", "ϋ", "Α", "Β", "Γ", "Δ", "Ε",
                  "Ζ", "Η", "Θ", "Ι", "Κ", "Λ", "Μ", "Ν", "Ξ", "Ο", "Π", "Ρ", "Σ", "Τ", "Υ", "Φ", "Χ", "Ψ", "Ω"]
    new_letter = ["α", "ε", "η", "ι", "ο", "υ", "ω", "α", "ε", "η", "ι", "ο", "υ", "ω", "υ", "α", "β", "γ", "δ", "ε",
                  "ζ", "η", "θ", "ι", "κ", "λ", "μ", "ν", "ξ", "ο", "π", "ρ", "σ", "τ", "υ", "φ", "χ", "ψ", "ω"]

    for i in range(len(old_letter)):
        text = text.replace(old_letter[i], new_letter[i])
    return text


# returns the title of the page
def get_title(soup):
    if hasattr(soup.title, 'string'):
        return soup.title.string
    else:
        return ""


# returns the description of the page
def get_description(soup, text):
    flag = True
    description = ''  # will store our final description of the page
    try:
        content = soup.find('meta', {'name': 'description'})
        if content:
            desc = content['content']
        else:
            content = soup.find("meta", property="og:description")
            if content:
                desc = content['content']
            else:
                # in case there is no known description
                desc = text
    except:  # catch *all* exceptions
        print("description error")
        flag = False

    if not flag:
        desc = text

    # in case the description has more than 10 words, crop it
    splitted = desc.split()
    if len(splitted) >= 10:
        for i in range(10):
            description = description + " " + splitted[i]
    else:
        for i in range(len(splitted)):
            description = description + " " + splitted[i]
    description = description + "..."
    return description


# returns the text that the page has page
def get_text(soup):
    for script in soup("script"):
        script.decompose()
    text = soup.get_text()
    text = process_text(text)
    return text


# will put all of our data inside a list, so we can put it in the dictionary
def list_all_doc_data(link, title, description, text):
    temp = []
    temp.append(link)
    temp.append(title)
    temp.append(description)
    temp.append(text)
    return temp


def Merge(new, old):
    for data in new:
        old[data] = new[data]
    return old

# variables needed
document_data = {}
indexer_data = {}
link_ids = 1
titles = []
links = set()
number_of_pages_crawled = 0
pages_for_index_update = 20
links_queue = Queue()

def mainCrawlLoop(lock):
    global document_data,indexer_data,link_ids,titles,links,number_of_pages_crawled,links_queue
    old_index_data = {}
    while number_of_pages_crawled < number_of_pages and links_queue.empty() is False:
        link = links_queue.get() # get first link in queue
        try:
            if '#' not in link and 'https://' in link or 'http://' in link:
                agent = {"User-Agent":'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'}
                res = requests.get(link, headers=agent) # get first link in queue
                soup = BeautifulSoup(res.text, "html.parser")
                title = get_title(soup)
                if title not in titles:
                    titles.append(title)
                    text = get_text(soup)
                    description = get_description(soup, text)
                    data = list_all_doc_data(link, title, description, text)
                    # Lock for concurrency
                    lock.acquire()
                    # Check to see if finished
                    if number_of_pages_crawled >= number_of_pages:
                        lock.release()
                        break
                    document_data[link_ids] = data
                    indexer_data[link_ids] = data
                    print("link_ids", link_ids)
                    print(link)
                    link_ids += 1
                    number_of_pages_crawled += 1

                    if (link_ids-1) % pages_for_index_update == 0:  # send the links to indexer
                        # will contain all our data
                        with open('document_data.json', 'w') as fp:
                            json.dump(document_data, fp, indent=2)
                        # temporally contains new data for the indexer, indexer will delete them
                        # we need to read the old index_data first, in case its not empty
                        if getsize('index_data.json') > 2:
                            with open('index_data.json') as json_file:
                                old_index_data = json.load(json_file)
                        else:
                            old_index_data = {}
                        indexer_data = Merge(indexer_data, old_index_data)
                        with open('index_data.json', 'w') as fp:
                            json.dump(indexer_data, fp, indent=2)
                        indexer_data = {}
                        print("send to index")
                    lock.release()
                    new_links = soup.find_all('a', href=True)
                    for l in new_links:
                        new_link = l['href']
                        if new_link[0] == '/':
                            if link[4] == 's':
                                http = 'https://'
                            else:
                                http = 'http://'
                            domain = link.split(http)[1].split('/')[0]
                            new_link = http + domain + new_link
                        if new_link not in links and links_queue.full() == False:
                            links_queue.put(new_link)
                            links.add(new_link)
                    links.add(link)

        except Exception as e:  # catch *all* exceptions
                print(e)

def crawler(starting_link, number_of_pages,number_of_threads):
    global document_data,link_ids,titles,links,number_of_pages_crawled,links_queue
    if os.path.isfile("document_data.json"):    #if we wish to retain old data
        with open('document_data.json') as json_file:
            document_data = json.load(json_file)
        link_ids = len(document_data) + 1
        values = document_data.values()
        titles = [value[1] for value in values]
        print("Reading old files\n")

    old_index_data = {}
    # creates the data document we want to send to indexer
    with open('index_data.json', 'w') as fp:
        json.dump(old_index_data, fp, indent=2)
    links_queue = Queue(maxsize = number_of_pages) # contains links left to explore

    #explore starting link
    link = starting_link
    if '#' not in link and 'https://' in link or 'http://' in link:
        agent = {"User-Agent":'Mozilla/5.0 (Windows NT 6.3; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'}
        res = requests.get(link, headers=agent) # get first link in queue
        soup = BeautifulSoup(res.text, "html.parser")
        new_links = soup.find_all('a', href=True)
        for l in new_links:
            new_link = l['href']
            if new_link[0] == '/':
                if link[4] == 's':
                    http = 'https://'
                else:
                    http = 'http://'
                domain = link.split(http)[1].split('/')[0]
                new_link = http + domain + new_link
            if links_queue.full() == False:
                links_queue.put(new_link)
                links.add(new_link)

    thread_list = []
    lock = threading.Lock()

    for i in range(0,number_of_threads):
        thread = threading.Thread(target=mainCrawlLoop, args=(lock,))
        thread_list.append(thread)
    for thread in thread_list:
        thread.start()
    for thread in thread_list:
        thread.join()

    if(links_queue.empty()):
        print("\n")
        print("No more links left!")
    else:
        print("\n")
        print(number_of_pages,"pages crawled!")
    print("======")
    return links, titles, document_data

if len(sys.argv) == 1:
    starting_link = "https://stackoverflow.com/"
    number_of_pages = 400
    delete_database()
    number_of_threads = 4
elif len(sys.argv) == 5:
    starting_link = sys.argv[1]
    number_of_pages = int(sys.argv[2])
    if sys.argv[3] == '0':
        delete_database()
    number_of_threads = int(sys.argv[4])
else:
    print("Wrong number of arguments")
    exit()
links, titles, document_data = crawler(starting_link, number_of_pages,number_of_threads)

with open('document_data.json', 'w') as fp:
    json.dump(document_data, fp, indent=2)
