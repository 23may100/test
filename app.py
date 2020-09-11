import os
import re
import json
import requests
from flask import Flask, request, make_response, jsonify, url_for, send_from_directory
from flask_socketio import SocketIO, emit
import pygal
import base64
from flask_cors import CORS
import jupyter_client as jc
import threading

import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

global session_count;
session_count = 0;

active_userind = -1;
dialogue_file = 'dialogue';
dfile = open(dialogue_file);
session_ids = list();
sessionmap = dict();
#result_map: session_ids -> code_segments -> results
result_map = dict();
result_map_lock = threading.Lock()
admin_sid = str();

#dialogue utterance structurez
#uncomment this thing later
init_question = {'name': 'GRIT', 'question' : '', 'code': '', 'images': [] , 'relation': ''};
flag = False;
for line in dfile:
    line = line.strip();
    splits = line.split();
    if len(splits) > 0 and splits[0].isnumeric():
        if int(splits[0]) > 0:
            break;
        init_question['question'] = ' '.join(splits[2:]);
    elif len(splits) > 0 and splits[0] == 'code':
        flag = True;
    elif flag:
        if line == 'end':
            flag = False;
            continue;
        init_question['code'] += (line + '\n')
    elif splits[0] == 'image':
        init_question['images'] = splits[1:];

init_conversation = [init_question];

# init_conversation = []

def hello(id, input):
    if 'hello' in input:
        output = "Hello, how are you?"

    elif input == 'I want a barchart with title MyBarchart with categories category1 and category2 and data 2,3,4,2,3,4 and 2,3,4,3,4,3,4':
        output = Barchart(id, 'MyBarchart',
                          'category1,2,3,4,2,3,4:category2,2,3,4,3,4,3,4')
    elif input == 'I want a piechart with title MyPieChart with categories category1 and category2 and data 70 and 30':
        output = Pie(id, 'MyPieChart',
                          'category1,70:category2,30')
    elif input == 'I want a scatterplot with title Myscatterplot with categories category1 and category2 and data (1,2).(2,2).(1,3) and (2,3).(2,3).(4,2).(4,2)':
        output = Scatter(id, 'Myscatterplot',
                          'category.(1,2).(2,2).(1,3):category2.(2,3).(2,3).(4,2).(4,2)')
    elif input == 'I want a linechart with title Mylinechart with categories category1 and data 20,30,40,20,30,40':
        output = Linechart(id, 'Mylinechart',
                          'category1,20,30,40,20,30,40')
    else:
        output = ''
    return output


# data format Category1,1,2,3,4,5:Category2,2,3,4,6,6,7,3,4,2:Category3,2,3,4,5,2,3,4
def Barchart(id, title, data):

    bar_chart = pygal.Bar()
    bar_chart.title = title

    data_cols = data.split(':')
    for x in range(0, len(data_cols)):
        data_num = []
        data_cols_split = data_cols[x].split(',')

        for y in range(1, len(data_cols_split)):
            print(data_cols_split[y])
            data_num.append(int(data_cols_split[y]))

        bar_chart.add(str(data_cols_split[0]), data_num)

    bar_chart.render_to_png('barchart.png')

    with open("barchart.png", "rb") as imageFile:
        imgstring = base64.b64encode(imageFile.read())



    return (imgstring)


# data format Category1,1,2,3,4,5:Category2,2,3,4,6,6,7,3,4,2:Category3,2,3,4,5,2,3,4
def Linechart(id, title, data):
    line_chart = pygal.Line()
    line_chart.title = title

    data_cols = data.split(':')
    for x in range(0, len(data_cols)):
        data_num = []
        data_cols_split = data_cols[x].split(',')

        for y in range(1, len(data_cols_split)):
            print(data_cols_split[y])
            data_num.append(int(data_cols_split[y]))

            print(data_num)
        line_chart.add(str(data_cols_split[0]), data_num)

    line_chart.render_to_png('linechart.png')

    with open("linechart.png", "rb") as imageFile:
        imgstring = base64.b64encode(imageFile.read())
    return imgstring

def Pie (id,title,data): ##data format Category1,25:Category2,75
    pie_chart = pygal.Pie()
    pie_chart.title = title

    data_cols = data.split(':')
    for x in range(0,len(data_cols)):
        data_num = []
        data_cols_split = data_cols[x].split(',')


        for y in range(1,len(data_cols_split)):
            print(data_cols_split[y])
            data_num.append(int(data_cols_split[y]))

            print(data_num)
        pie_chart.add(str(data_cols_split[0]), data_num)
    pie_chart.render_to_png('pie.png')

    with open("pie.png", "rb") as imageFile:
        imgstring = base64.b64encode(imageFile.read())
    return imgstring

def Scatter(id,title,data): ## data format  category.(1,2).(2,2).(1,3):category2.(2,3).(2,3).(4,2).(4,2)
    scatter_chart = pygal.XY(stroke=False)
    scatter_chart.title = title
    data_cols = data.split(':')
    for x in range(0,len(data_cols)):
        data_num = []
        data_cols_split = data_cols[x].split('.')

        for y in range(1,len(data_cols_split)):
            print(data_cols_split[y])
            data_num.append(data_cols_split[y])
        print(data_num)
        scatter_chart.add(str(data_cols_split[0]), [literal_eval(strtuple) for strtuple in data_num])

        scatter_chart.render_to_png('scatter.png')

    with open("scatter.png", "rb") as imageFile:
        imgstring = base64.b64encode(imageFile.read())
    return imgstring


application = Flask(__name__,static_folder='static')
# application = Quart(__name__,static_folder='static')
app = application
socketio = SocketIO(app, async_mode='threading')

@app.route('/', methods=['GET', 'POST'])
def index():
    print("index function was called")
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/static/<file_name>')
def static_file(file_name):
    return send_from_directory(app.static_folder, file_name)

@app.route('/favicon.ico')
def icon():
    return '';


@app.route('/admin', methods=['GET', 'POST'])
def admin_index():
    print("index function was called")
    return send_from_directory(app.static_folder, 'admin_index.html')

@app.route('/admin_static/<file_name>')
def admin_static_file(file_name):
    return send_from_directory(app.static_folder, file_name)

@app.route('/pics/<image_name>')
def get_image(image_name):
    print('Asked for an image!', image_name)
    return send_from_directory('./pics/', image_name)

@socketio.on('uname')
def handle_connection(json):
    # print('**************Session ID:', request.sid)
    global session_count
    #start the kernel for this user
    # kernel_id = kernel_man.start_kernel()
    kernel_manager = jc.KernelManager()
    kernel_manager.start_kernel()
    # sessionmap[request.sid]['kernel_client'] = kernel_manager.blocking_client()
    global admin_sid;
    if json['data'] == 'admin':
        emit('connected_users', len(sessionmap))
        admin_sid = request.sid
    else:
        print('******** Initial Convo: ', init_conversation);
        sessionmap[request.sid] = {'conversation' : list(init_conversation), 'kernel_client' : kernel_manager.blocking_client()}
        sessionmap[request.sid]['kernel_client'].start_channels()

        session_ids.append(request.sid)

        emit('uname', 'user' + str(len(sessionmap)))
        emit('init_convo', init_conversation)
        if admin_sid != '':
            emit('new_user', 'user' + str(len(sessionmap)), room=admin_sid)
    return

@socketio.on('getid')
def getid():
    print("getid function was called")
    newid = 0
    return str(newid)

def msg_recvd():
    print("I got the message");


# def handle_code_reply(exec_result):
#     #execute_result, display_data, stream, execute_reply
#     if exec_result['header']['msg_type'] == 'error':
#         emit('code_exec_result', {'type': 'error', 'content' : exec_result['content']})
#     elif exec_result['header']['msg_type'] in ['execute_result', 'display_data', 'stream']:
#         emit('code_exec_result', {'type': exec_result['header']['msg_type'], 'content' : exec_result['content']})




@socketio.on('code_exec_request')
def exec_request(code):
    print('Code ID:', code['id'], request.sid == admin_sid)
    global result_map
    result_map_lock.acquire()
    try:
        print("************I am here after the lock!")
        #shared region
        current_sid = None
        if request.sid == admin_sid:
            current_sid = session_ids[active_userind]
        else:
            current_sid = request.sid


        if current_sid not in result_map:
            result_map[current_sid] = dict()

        def handle_code_reply(exec_result, id=code['id']):
            print("************Execution Result\n", exec_result)
            if exec_result['header']['msg_type'] == 'error':
                
                result_dict = dict({'type': 'error', 'content' : exec_result['content']})
                if code['code'] in result_map[current_sid]:
                    result_map[current_sid][code['code']].append(result_dict);
                else:
                    result_map[current_sid][code['code']] = list([result_dict]);
                print("^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^This is the state of result map after the error: ", \
                    result_map[current_sid][code['code']])
                emit('code_exec_result', {'type': 'error', 'content' : exec_result['content'], 'id' : id})
            
            elif exec_result['header']['msg_type'] in ['execute_result', 'display_data', 'stream']:

                result_dict = dict({'type': exec_result['header']['msg_type'], 'content' : exec_result['content']})
                if code['code'] in result_map[current_sid]:
                    result_map[current_sid][code['code']].append(result_dict);
                else:
                    result_map[current_sid][code['code']] = list([result_dict]);
                emit('code_exec_result', {'type': exec_result['header']['msg_type'], 'content' : exec_result['content'], \
                    'id' : id})

        if ('override' not in code) and (code['code'] in result_map[current_sid]):
            # print('Code Signature and Previous Store', code, result_map[current_sid])
            for segment in result_map[current_sid][code['code']]:
                temp_result = {k : v for k, v in segment.items()}
                temp_result['id'] = code['id']
                # print('This is the previously Stored result for code*************:', temp_result)
                emit('code_exec_result', temp_result)
        else:
            sessionmap[current_sid]['kernel_client'].execute_interactive(code['code'], output_hook=handle_code_reply)
    finally:
        result_map_lock.release()

#@app.route('/sendout',methods=['POST'])
flag = True
@socketio.on('sendout')
def inputoutput(json):
    global flag
    # print('**************Session ID:', request.sid)
    # print("inputoutput function was called!", json)
    my_response = hello(json['name'],json['message'])
    sessionmap[request.sid]['conversation'].append(json)
    if active_userind != -1 and session_ids[active_userind] == request.sid:
        emit('response', json, room=admin_sid)
    # if json.code != '':
    #     sessionmap[request.sid]['kernel_client'].execute_interactive(code, outout_hook=handle_code_reply)
    response = {'name' : 'GRIT', 'question' : 'Good Job. Next, write a function which gives the sum of all columns of a table.', \
        'code' : '', 'relation' : '', 'images' : ''}
    sessionmap[request.sid]['conversation'].append(response)
    if flag:
        emit('response', response)
        flag = False
    # emit('response', {'name' : 'Bot', 'question' : 'Good Job', \
    #     'code' : '', 'relation' : '', 'images' : ''}, broadcast=True, include_self=False)

@socketio.on('admin_sendout')
def admin_inputoutput(json):
    print('&&&&&&&&&&&&&&&&&&&&&&&Admin Sendout event received with following json:', json);
    current_sid = session_ids[active_userind]
    emit('response', json, room=current_sid)
    sessionmap[current_sid]['conversation'].append(json)

@socketio.on('ask_for_convo')
def ask_convo(uname):
    # print('**************Session ID:', request.sid)
    # print("inputoutput function was called!", json)
    # my_response = hello(json['name'],json['message'])
    ix = int(uname[4:]) - 1
    global active_userind
    active_userind = ix
    emit('init_convo', sessionmap[session_ids[ix]]['conversation'])

@socketio.on('disconnect')
def handle_close():
    print('socket closed')
    if request.sid != admin_sid:
        with open('./conversations/' + str(request.sid) + '_convo.json', 'w') as conv_file:
            json.dump(sessionmap[request.sid]['conversation'], conv_file, indent=4)

socketio.run(app, debug=True)



