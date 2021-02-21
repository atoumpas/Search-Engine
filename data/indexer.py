# coding=utf-8
import os
import random
import json
import math
from os.path import getsize
import time
from queue import Queue
import threading


def mainNormLoop(doc):
    global dif_words_queue, dif_words, norms
    unique_words = []
    counter = 0
    splitted = index_data[doc][3].split()
    for word in splitted:
        if word not in unique_words:
            unique_words.append(word)
            counter += 1 
        if word not in dif_words:
            dif_words.append(word)
            dif_words_queue.put(word)#####
    norms[doc] = math.sqrt(counter)



# gets a dictionary with our new documents named dict
# the previous inverted index named total_inverted_dict
# the previous norms named total_norms
# creates the inverted_dict
def inverted_index(number_of_threads):
    global dif_words_queue, inverted_dict, dif_words, unique_words, all_keys, norms ####
    global total_inverted_dict, index_data, total_norms
    dif_words_queue = Queue() # contains words left to explore ####

    s = time.time()
    keys = list(index_data.keys())
    # find all diffirent words on our documents, and also the number of unique words for each document
    norms = {}
    dif_words = []  # all tha diffirent words

    thread_list = []
    
    for i in range(0,len(keys)):
        thread = threading.Thread(target=mainNormLoop, args=(keys[i],))
        thread_list.append(thread)
    for thread in thread_list:
        thread.start()
    for thread in thread_list:
        thread.join()
    
    print("threads done")
    # adding norms for each document, depending if we already had a norm file or not
    if total_norms:
        for doc in norms:
            total_norms[doc] = norms[doc]
    else:
        total_norms = norms.copy()

    print (time.time() - s)
    #inverted_dict = {}  # will contain the final inverted index (διαγράφει [[2, 0.2]])
    #thread_list = []

    

    # for each diffirent word, count how many times it appears in every document
    inverted_dict = {}  # will contain the final inverted index (διαγράφει [[2, 0.2]])
    for word in dif_words:
        inverted = []  # contains two values ( [in which document, frequency] ) or [[2, 0.2]]
        for i in index_data.keys():
            if index_data[i][3].count(word) != 0:
                temp = []
                temp.append(i)
                temp.append(index_data[i][3].count(word))  # frequency
                inverted.append(temp)
        inverted_dict[word] = inverted

     # in case inverted index wasnt empty, we merge the old one with the new one, otherwise we create the new inverted
    if total_inverted_dict:
        print("not empty")
        for word in inverted_dict:  # for each word in the inverted we just created
            if word in total_inverted_dict:  # check if its already inside the total inverted
                for lst in inverted_dict[word]:  # add each list that is inside the list of that word in the dict
                    total_inverted_dict[word].append(lst)
            else:  # if the word isnt inside the total inverted, we just add it
                total_inverted_dict[word] = inverted_dict[word]
    else:
        print("empty")
        total_inverted_dict = inverted_dict.copy()
        
    s = time.time()
    # write dicts in json files
    with open('norms.json', 'w') as fp:
        json.dump(total_norms, fp, indent=2)

    with open('inverted_index.json', 'w') as fp:
        json.dump(total_inverted_dict, fp, indent=2)
    print("file time", time.time() - s)
    return total_inverted_dict, total_norms



# in case there is no index_data file at all, creats an empty one, until crawler sends his data
if not (os.path.exists('index_data.json')):
    index_data = {}
    with open('index_data.json', 'w') as fp:
        json.dump(index_data, fp, indent=2)

start = time.time()
# run for one hour
one_hour = 60 * 60
number_of_threads = 8
#global total_inverted_dict, index_data, total_norms
while (time.time() - start < one_hour):
    # if crawler has sent us new data
    if getsize('index_data.json') > 2:
        time.sleep(0.1) #add delay in case file is still being written
        s = time.time()
        try:
            with open('index_data.json') as json_file:
                index_data = json.load(json_file)

            # check if we already have an inverted index
            if os.path.exists('inverted_index.json'):
                with open('inverted_index.json') as json_file:
                    total_inverted_dict = json.load(json_file)
                with open('norms.json') as json_file:
                    total_norms = json.load(json_file)
            else:
                total_inverted_dict = {}
                total_norms = {}

            # total_inverted_dict is our previous inverted and we want to update it, if empty it creates a new one
            total_inverted_dict, total_norms = inverted_index(number_of_threads)
        
            end = time.time()
            # index_data should be emptied here
            indexer_data = {}
            with open('index_data.json', 'w') as fp:
                json.dump(indexer_data, fp, indent=2)
        except:
            print("file was curently being used by crawler")
        print("total time", end - s)

# for word in total_norms:
#    print word, total_norms[word]
# for word in total_inverted_dict:
#    print word, total_inverted_dict[word]
# print("=========================")
