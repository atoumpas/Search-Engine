# coding=utf-8
import os
import random
import json
import math
from os.path import getsize
import time
from queue import Queue
import threading



def mainInvertedLoop (lock):
    global dif_words_queue, inverted_dict, total_inverted_dict, dict, total_norms
    word = dif_words_queue.get() # get first word in queue

    inverted = []  # contains two values ( [in which document, frequency] ) or [[2, 0.2]]
    for i in dict.keys():
        if dict[i][3].count(word) != 0:
            temp = []
            temp.append(i)
            temp.append(dict[i][3].count(word)) 
            inverted.append(temp)
    inverted_dict[word] = inverted
    


# gets a dictionary with our new documents named dict
# the previous inverted index named total_inverted_dict
# the previous norms named total_norms
# creates the inverted_dict
def inverted_index(number_of_threads):
    global dif_words_queue, inverted_dict ####
    global total_inverted_dict, dict, total_norms
    dif_words_queue = Queue() # contains words left to explore ####
    
    # find all diffirent words on our documents, and also the number of unique words for each document
    norms = {}
    dif_words = []  # all tha diffirent words
    for i in dict.keys():
        unique_words = []
        counter = 0
        splitted = dict[i][3].split()
        for word in splitted:
            if word not in unique_words:
                unique_words.append(word)
                counter += 1
            if word not in dif_words:
                dif_words.append(word)
                dif_words_queue.put(word)#####
        norms[i] = math.sqrt(counter)

    # adding norms for each document, depending if we already had a norm file or not
    if total_norms:
        for doc in norms:
            total_norms[doc] = norms[doc]
    else:
        total_norms = norms.copy()
        
    inverted_dict = {}  # will contain the final inverted index (διαγράφει [[2, 0.2]])
    

    thread_list = []
    lock = threading.Lock()

    for i in range(0,number_of_threads):
        thread = threading.Thread(target=mainInvertedLoop, args=(lock,))
        thread_list.append(thread)
    for thread in thread_list:
        thread.start()
    for thread in thread_list:
        thread.join()


    if total_inverted_dict:
        print("not empty")
        for word in inverted_dict:  # for each word in the inverted we just created
            if word in total_inverted_dict:  # check if its already inside the total inverted
                for list in inverted_dict[word]:  # add each list that is inside the list of that word in the dict
                    total_inverted_dict[word].append(list)
            else:  # if the word isnt inside the total inverted, we just add it
                total_inverted_dict[word] = inverted_dict[word]
    else:
        print("empty")
        total_inverted_dict = inverted_dict.copy()
    

    # write dicts in json files
    with open('norms.json', 'w') as fp:
        json.dump(total_norms, fp, indent=2)

    with open('inverted_index.json', 'w') as fp:
        json.dump(total_inverted_dict, fp, indent=2)

    return total_inverted_dict, total_norms



# in case there is no index_data file at all, creats an empty one, until crawler sends his data
if not (os.path.exists('index_data.json')):
    index_data = {}
    with open('index_data.json', 'w') as fp:
        json.dump(index_data, fp, indent=2)

start = time.time()
# run for one hour
one_hour = 60 * 60
number_of_threads = 20
global total_inverted_dict, dict, total_norms
while (time.time() - start < one_hour):
    
    
    # if crawler has sent us new data
    if getsize('index_data.json') > 2:
        time.sleep(2) #add delay in case file is still being written
        with open('index_data.json') as json_file:
            dict = json.load(json_file)

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

        print(end - start)

# for word in total_norms:
#    print word, total_norms[word]
# for word in total_inverted_dict:
#    print word, total_inverted_dict[word]
# print("=========================")
