# coding=utf-8
import json
import sys
import math

def mainLoop(word,lock):
    if word in dictionary:
        tuples = dictionary[word]
        nt = len(tuples)
        if sys.argv[1] == 'search':
            weight = math.log(1 + N / nt)
            data['weights'][word] = weight
        else:
            weight = data['weights'][word]
        for tuple in tuples:
            documentID = tuple[0]
            freq = tuple[1]
            if documentID not in sum:
                sum[documentID] = 0
            TF = 1 + math.log(freq)
            lock.acquire()
            sum[documentID] += TF * weight
            lock.release()
    else:
        data['weights'][word] = 0
        
        

with open('temp.json') as json_file:
    data = json.load(json_file)

with open('document_data.json') as json_file:
    pages = json.load(json_file)
N = len(pages)
with open('inverted_index.json') as json_file:
    dictionary = json,load(json_file)

sum = {}
thread_list = []
lock = threading.Lock()
for i in range(0,len(data['search'])):
    thread = threading.Thread(target=mainLoop, args=(data['search'][i],lock,))
    thread_list.append(thread)
for thread in thread_list:
    thread.start()
for thread in thread_list:
    thread.join()


todump = []
todump.append(sum)
todump.append(data['weights'])

with open('temp.json', 'w') as fp:
    json.dump(todump, fp, indent=2)

    
               
