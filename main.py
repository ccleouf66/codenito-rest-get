#!/usr/bin/python3.8
from flask import Flask, json, request, Response
from datetime import datetime, timedelta, date
import os
import json
import time
import jsonify
from flask_cors import CORS, cross_origin
from calendar import monthrange
import random


status_hosts_values={"up":0, "down":1, "unreachable":2}
status_services_values={"nominal":0, "warning":1, "critical":2, "unknown":3}
status_values={"nominal":0,"up":0,"down":1,"critical":2,"warning":1,"unhknown":3}

tags=[]
columns=["critical", "warning", "nominal", "up", "down", "unknown","comment"]
api = Flask(__name__)
CORS(api, 
    expose_headers='Authorization',
    allow_headers=["Content-Type", "Authorization", "Access-Control-Allow-Credentials"],
    supports_credentials=True)

root_dir_data = "./"
separators=[",",";"]

class dataset:
    def __init__(self, name):
        self.targets=name
        self.datapoints=[]
        
    def add_point(self,metric, date, data):
        if metric == "comment":

          self.datapoints.append([data,date])
        else:
          self.datapoints.append([float(data),date])
        
    def get_json(self):
        return json.dumps(self)

class DatasetEncoder(json.JSONEncoder):
    def default(self, obj):
            return {
                    "target": obj.targets,
                    "datapoints": obj.datapoints
                 }

class object_data:
    def __init__(self, date):
        self.date=date
        self.data={}
        for t in tags:
            self.data[t]=""
        for t in columns:
            self.data[t]=0
            
    def csv_string(self):
        words=[]
        words.append(date)
        for t in tags:
            words.append(data[t])
        for t in columns:
            words.append(data[t]) 
            
def get_date(date_string):
    tmp = date_string[:len(date_string)-5]
    # print (date_string+" > "+tmp)
    return  datetime.strptime(tmp, '%Y-%m-%dT%H:%M:%S')

def create_file_test(name):
    time = name[2:].split('.')[0].split('-')
    with open(name, 'w') as f:
        f.write('date;critical;warning;nominal;up;down;unknown;comment;\n')
        for i in range(1,32):
            print (i)
            f.write(time[0]+"/"+time[1].zfill(2)+"/"+str(i).zfill(2)+";10;20;30;40;50;60;\n")
        f.close()

def create_file(name):
    print("Create File : "+name)
    time = name[2:].split('.')[0].split('-')
    year=int(time[0])
    month=int(time[1])

    status_values, hosts_results, services_results = query_month(month, year)
    with open(name, 'w') as f:
      f.write('date;critical;warning;nominal;up;down;unknown;comment;\n')
      for i in range(1,monthrange(year,month)[1]+1):
        date_string = time[0]+"/"+time[1].zfill(2)+"/"+str(i).zfill(2)
        print ("searching "+date_string)
        critical=0
        warning=0
        nominal=0
        up=0
        down=0
        unknown=0
        comment=""

        for status in status_hosts_values:
            #print (str(status)+"  "+str(status_values[status]))
            for line in hosts_results[status]:
                t=date.fromtimestamp(int(line[0]))
                if t.month==month and t.year==year and i==t.day:
                    if status == "up":
                        up = str(line[1])
                    if status == "down":
                        down = str(line[1])
#                    if status == "warning":
#                        unknown = str(line[1])
        for status in status_services_values:
            for line in services_results[status]:
                t=date.fromtimestamp(int(line[0]))
                if t.month==month and t.year==year and i==t.day:
                    if status == "nominal":
                        nominal = str(line[1])
                    if status == "critical":
                        critical = str(line[1])
                    if status == "warning":
                        warning = str(line[1])

        print (date_string+";"+str(critical)+";"+str(warning)+";"+str(nominal)+";"+str(up)+";"+str(down)+";"+str(unknown)+";"+comment+";")
        f.write(date_string+";"+str(critical)+";"+str(warning)+";"+str(nominal)+";"+str(up)+";"+str(down)+";"+str(unknown)+";"+comment+";\n")
    f.close()
    
def read_file(name):
    data_columns = None
    separator=None
    data_table = []

    if not os.path.exists(name):
      create_file(name)
    with open(name) as f:
        while True: 
            line = f.readline()
            
            if data_columns == None:
                if separator == None:
                    for separator in separators:
                        data_columns = line.split(separator)    
                        if len(data_columns)>1:
                            # print ("Use "+separator+" as separator")
                            break
                data_columns = line.split(separator)
            else:
                data_table.append(line.split(separator))
            if not line:
                break
            
            # print(line.strip())
    
    return data_columns, data_table        
        
def between(date, date_from, date_to):
    ts = time.mktime(datetime.strptime(date,"%Y/%m/%d").timetuple())
    return (ts >= date_from.timestamp() ) and (ts <= date_to.timestamp() )

def read_data(range, metric):
    #2022-12-16T15:16:36.434Z
    date_from =get_date(range["from"])
    date_to =get_date(range["to"])
    print ("From :"+str(date_from))
    print ("To   :"+str(date_to))
    # print (date_from.date())
    # print (date_to.date())
    files=[]
    current = date_from
    
    while not ((current.date().year == date_to.date().year) and (current.date().month==date_to.date().month)):
        print ("current :"+str(current)) 
        tmp = str (current.year)+"-"+str(current.month)
        if not tmp in files:
            files.append(tmp)
            # print (tmp)

        current = current + timedelta(days=1)
    tmp = str (current.year)+"-"+str(current.month)
    
    # print (tmp)
    
    if not tmp in files:
        files.append(tmp)

    data_dataset=dataset(metric)
    for _file in files:
        # print (_file)
        data_columns, data_table = read_file( root_dir_data + _file + ".csv" )
        index_date  = data_columns.index("date")
        index_metric  = data_columns.index(metric)
        for point in data_table:
            if len(point)>= index_metric+1 and len(point)>= index_date+1:
                if between (point[index_date] , date_from, date_to):
                    data_dataset.add_point(metric,point[index_date], point[index_metric])
    return data_dataset

@api.route('/search', methods=['POST'])
def search():
    c=[]
    for v in columns:
      c.append({"type":"integer","text":v})
    return json.dumps(columns)
    
#  print (request.get_json())  
#  return json.dumps(
#          ["value","comment"]
#          [ { "text": "upper_25", "value": 1}, { "text": "upper_75", "value": 2} ]
#          )
#print(line.strip())

@api.route('/', methods=['GET'])
def root():
    return "OK"

@api.route('/random', methods=['GET'])
def random():


    return random.randint(0,9)

processing=False
@api.route('/query', methods=['POST'])
def query():
    global processing
    while(processing):
        time.sleep(10)

    processing=True
    datas=[]
    for target in request.json["targets"]:
        data = read_data(request.json["range"],target["target"])
        datas.append(data)
    processing=False
    return json.dumps(datas, cls=DatasetEncoder)
# data.get_json()
    """  return json.dumps( 
        [
            {
                "target":"pps in",
                "datapoints":[
                  [622,1450754160000],
                  [365,1450754220000]
                ]
            }
        ]
    ) """

    
# api_v2_cors_config = {
#   "origins": ["*"],
#   "methods": ["OPTIONS", "POST"],
#   "allow_headers": ["Authorization", "Content-Type", "Referer","accept"]
# } 


def update_file(object):
    print (" update data with "+str(object))
    date=object['date'].split(' ')[0]
    print (date)
    separator=None
    name=str(date.split('-')[0])+"-"+str(int(date.split('-')[1]))+".csv"
    print ("open "+name)
    lines=[]
    with open(name) as f:
        while True:
            line=f.readline()
            lines.append(line)
            if not line:
                break
        f.close()

    new_lines = []
    for line in lines:
            if separator == None:
               for separator in separators:
                  data_columns = line.split(separator)
                  if len(data_columns)>1:
                            # print ("Use "+separator+" as separator")
                       break
               data_columns = line.split(separator)
            else:
                data=line.split(separator)
                if data[0] == date.replace("-","/"):
                    print (date+" found")
                    data_line=[data[0],
                            str(object['critical']),
                            str(object['warning']),
                            str(object['nominal']),
                            str(object['up']),
                            str(object['down']),
                            str(object['unknown']),
                            object['comment'],
                            "\n"]
#                    'date;critical;warning;nominal;up;down;unknown;comment;
                    line = ";".join(data_line)
                else:
                    print (data[0])
            new_lines.append(line)

    with open(name, 'w') as f:
        for line in new_lines:
            #print (line)
            f.write(line)
        f.close()



@api.route('/edit', methods=['POST'])
# @cross_origin(origin='*',**api_v2_cors_config)
def edit():
    date = request.json['date'].split(' ')[0]
    print (request.json)
    update_file(request.json)
    resp = Response("Foo bar baz")
    return resp

# response = jsonify({"message":"OK"})
# respons.add

@api.route('/variable', methods=['GET'])
def variable():
  return json.dumps([])

@api.route('/tag-keys', methods=['GET'])
def tag_keys():
    tags=[]
    for v in columns:
      tags.append({"type":"string","text":v})
    return json.dumps(tags)

@api.route('/tag-values', methods=['GET'])
def tag_values():
  return json.dumps([])

if __name__ == '__main__':
   api.run(host='0.0.0.0', port=80)
