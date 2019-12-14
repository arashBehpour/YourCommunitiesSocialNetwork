from flask import Flask, render_template, request, make_response
from functools import wraps
import requests

import sys
import pika
import pymongo
import time
import json

db = pymongo.MongoClient().network_database # initalize mongoDB database for users
users_collection = db.users
topics_collection = db.topics
#audioFiles_collection = db.audioFiles --> for audio files to be sent, putting the string key into rabbitMQ instead of file

# Initalize RabbitMQ Service(exchanges/queues/bindings) on repository rpi
rabbitmq_user = "admin"
rabbitmq_pass = "pass"

global connection
global channel
credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)  #heartbeat=0 -> turns off heartbeat, maxLength = 65535
connection = pika.BlockingConnection(pika.ConnectionParameters('localhost', 5672, '/', credentials)) 
channel = connection.channel()

# Declare Initial Exchanges
channel.exchange_declare(exchange='VA-herndon', exchange_type='direct')
channel.exchange_declare(exchange='VA-blacksburg', exchange_type='direct')
channel.exchange_declare(exchange='VA-christiansburg', exchange_type='direct')
channel.exchange_declare(exchange='chat', exchange_type='direct')

# Declare Initial Queues
jiuJistuQueue = channel.queue_declare(queue='VA-herndon:jiuJistu')

# Initial Binding's
channel.queue_bind(exchange='VA-herndon', queue='VA-herndon:jiuJistu', routing_key='VA-herndon:jiuJistu')

# An Initial User and Topic
if db.users_collection.find_one({"User" : "admin"}) == None:
    db.users_collection.insert({ "User": "admin", "Password": "admin", "Topics": [], "Chats": [] })
    
if db.topics_collection.find_one({"Topic" : "VA-herndon:jiuJistu"}) == None:
    db.topics_collection.insert({"Topic" : "VA-herndon:jiuJistu"})
    
# Create any topic queues or exchanges that were previously made and stored in mongoDB
listOfTopics = db.topics_collection.find()
for cur in listOfTopics:
    strFullTopic = cur['Topic']
    splitList = strFullTopic.split(':')
    if len(splitList) > 1:
        channel.queue_declare(queue=strFullTopic)
        channel.exchange_declare(exchange=splitList[0], exchange_type='direct')
        channel.queue_bind(exchange=splitList[0], queue=strFullTopic, routing_key=strFullTopic)


#*****************************************************************************************************************************************
# REST Server side Application
app = Flask(__name__)

def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        
        if auth:
            result = db.users_collection.find_one({"User" : auth.username})
            if result != None:
                
                if result['Password'] == auth.password:
                    return f(*args, **kwargs)
                
                return make_response('Invalid password', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
                
            return make_response('User:' + auth.username + ' does not exist', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
            
        return make_response('Could not verify your login!', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

    return decorated


@app.route("/create/user", methods=['GET']) #FIXME: could be a POST
def createUser():
    
    new_username = request.args.get('username')
    new_password = request.args.get('password')
    
    if new_username != None and new_password != None:
        result = db.users_collection.find_one({"User" : new_username}) # check if username to be created is already in use. MAYBE: prevent user from making username with '+', ':'
        
        if result != None:
            response = {"Error" : "Username is already in use."}
        else:
            #chat_obj = {"friend" : None, "links" : []}
            new_user_document = { "User": new_username, "Password": new_password, "Topics": [], "Chats": [] }
            db.users_collection.insert(new_user_document)
            response = new_user_document
        
    else:
        response = {"Error" : "Need more information(username, password)."}
    
    templateData = {
        'title': "create/user",
        'response': response
    }
    
    return render_template('main.html', **templateData)
    
   
@app.route("/topics/produce", methods=['GET']) #FIXME: will change to be a POST
@auth_required
def topics_produce():
    
    username = request.args.get('user')
    message = request.args.get('mssg')
    location = request.args.get('loc') # Ex. Will come in like VA-herndon
    topic = request.args.get('topic') # Ex. jiuJistu
    
    if username != None and message != None and location != None and topic != None:
        result = db.users_collection.find_one({"User" : username}) # Check if username is valid
        community_topic = location + ":" + topic # Ex. Queue name and stored in mongoDB as VA-herndon:jiuJistu
        result2 = db.topics_collection.find_one({"Topic" : community_topic}) # check if valid topic in your community. MAYBE: prevent user from making topic as location (Ex. VA-herndon as topic)
        
        if result == None:
            response = {"Error" : "Username not valid."}
        else:
            
            global connection, channel # channel closes after a while of not being in use, need to reopen
            try: 
                curTopicQueue = channel.queue_declare(queue=community_topic)
            except:
                connection = pika.BlockingConnection(pika.ConnectionParameters('localhost', 5672, '/', credentials)) 
                channel = connection.channel()
                curTopicQueue = channel.queue_declare(queue=community_topic)
            
            if result2 == None: # Declare a new topic queue
                channel.queue_declare(queue=community_topic)
                channel.exchange_declare(exchange=location, exchange_type='direct')
                channel.queue_bind(exchange=location, queue=community_topic, routing_key=community_topic)
                db.topics_collection.insert({"Topic" : community_topic}) #Insert topic in database
            
            # Produce a message in rabbitMQ
            full_message = username + ": " + message
            channel.basic_publish(exchange=location, routing_key=community_topic, body=full_message)
            response = {"Topic" : topic, "Message" : full_message}
            
            # Add current Topic to Users info if it is not there
            if topic not in result['Topics']:
                newList = result['Topics'] + [topic]
                db.users_collection.update_one({"User" : username}, { "$set": { "Topics": newList} })
        
    else:
        response = {"Error" : "Need more information(user, mssg, loc, topic)."}
    
    templateData = {
        'title': "topics/produce",
        'response': response
    }
    
    return render_template('main.html', **templateData)
    
    
@app.route("/topics/consume", methods=['GET'])
@auth_required
def topics_consume():
    
    username = request.args.get('user')
    location = request.args.get('loc') # Ex. Will come in like VA-herndon
    topic = request.args.get('topic') # Ex. jiuJistu
    
    if username != None and location != None and topic != None:
        result = db.users_collection.find_one({"User" : username}) # Check if username is valid
        community_topic = location + ":" + topic # Ex. Queue name and stored in mongoDB as VA-herndon:jiuJistu
        result2 = db.topics_collection.find_one({"Topic" : community_topic}) # check if valid topic in your community
        
        if result == None:
            response = {"Error" : "Username not valid."}
        else:
            
            if result2 != None and topic in result['Topics']: #Check that the user has this topic subscribed to consume
                
                global connection, channel # channel closes after a while of not being in use, need to reopen
                try: 
                    curTopicQueue = channel.queue_declare(queue=community_topic)
                except:
                    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost', 5672, '/', credentials)) 
                    channel = connection.channel()
                    curTopicQueue = channel.queue_declare(queue=community_topic)
                
                
                global consumed_message
                consumed_message = ''
                
                def callback(ch, method, properties, body):
                    global consumed_message
                    consumed_message = body.decode()
                    ch.basic_ack(delivery_tag=method.delivery_tag) 
                    channel.stop_consuming() #Stop consuming
                
                if curTopicQueue.method.message_count != 0:
                    channel.basic_consume(callback, queue=community_topic)
                    channel.start_consuming()
                
                response = {"Topic" : topic, "Message" : consumed_message}
                
            else:
                response = {"Error" : "No such topic in your area to consume from. Or you are not subscribed to topic."}
    
    else:
        response = {"Error" : "Need more information(user, loc, topic)."}
    
    templateData = {
        'title': "topics/consume",
        'response': response
    }
    
    return render_template('main.html', **templateData)
    
    
@app.route("/topics/list", methods=['GET']) # list all topics near users location 
@auth_required
def topics_list():
    
    location = request.args.get('loc') # Will come in like VA-herndon
    username = request.args.get('user') # [option]list all topics user is subscribed too
    
    if location != None:
        
        if username != None:
            # output the topics you are subscribed too
            result = db.users_collection.find_one({"User" : username}) 
            
            if result == None:
                response = {"Error" : "Username not valid."}
            else:
                response = {"Topics" : result['Topics']}
            
        else:
            # output all topics in your area
            communityTopics = []
            for curTop in db.topics_collection.find({"Topic" : { "$regex": location + ':'}}):
                communityTopics.append(curTop['Topic'].split(':', 1)[1])
            
            response = {"Topics" : communityTopics}
        
    else:
        response = {"Error" : "Need more information([optional]user, loc)."}
    
    templateData = {
        'title': "topics/list",
        'response': response
    }
    
    return render_template('main.html', **templateData)
        
    
@app.route("/topics/unsubscribe", methods=['GET']) # remove a topic from users profile/data base
@auth_required
def topics_remove():
    
    topic = request.args.get('topic')
    username = request.args.get('user')
    
    if topic != None and username != None:
        result = db.users_collection.find_one({"User" : username}) # Check if username is valid
        
        if result == None:
            response = {"Error" : "Username not valid."}
        else:
            if topic in result['Topics']: # Remove current topic from your list
                newList = list(result['Topics'])
                newList.remove(topic)
                db.users_collection.update_one({"User" : username}, { "$set": { "Topics": newList} })
                response = {"Topic" : topic}
            else:
                response = {"Error" : "Topic to be unsubscribed is already unsubscribed from your topics list."}
                
    else:
        response = {"Error" : "Need more information(user, topic)."}
    
    templateData = {
        'title': "topics/unsubscribe",
        'response': response
    }
    
    return render_template('main.html', **templateData)
    

@app.route("/chats/list", methods=['GET']) # list all active chats user is interacting with
@auth_required
def chat_list():
    
    username = request.args.get('user')
    
    if username != None:
        result = db.users_collection.find_one({"User" : username}) # Check if username is valid
        
        if result == None:
            response = {"Error" : "Username not valid."}
        else:
            chatList = []
            for curChatFriend in result['Chats']:
                chatList.append(curChatFriend)
        
            response = {"Chats" : chatList}
    else:
        response = {"Error" : "Need more information(user)."}
    
    templateData = {
        'title': "chat/list",
        'response': response
    }
    
    return render_template('main.html', **templateData)


@app.route("/chats/create", methods=['GET']) # Build 2 queues to talk to each other
@auth_required
def chat_create():
    print("in chat create")

@app.route("/chats/produce", methods=['GET']) # FIXME: will change to be a POST
@auth_required
def chat_produce():
    print("in chat produce")
    
@app.route("/chats/consume", methods=['GET'])
@auth_required
def chat_consume():
    print("in chat consume")
    """
    curTopicQueue = channel.queue_declare(queue=community_topic)
    origMessageCount = curTopicQueue.method.message_count
    global consumed_message
    consumed_message = ''
    
    def callback(ch, method, properties, body):
        #print("%r:%r" % (method.routing_key, body)) #Display recieved/consumed message
        global consumed_message
        consumed_message = body.decode()
        print(method.delivery_tag)
        ch.basic_ack(delivery_tag=method.delivery_tag)
        #if consumed_message != '':
        channel.stop_consuming() #Stop consuming
    
    if origMessageCount != 0:
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(callback, queue=community_topic)#no_ack=True)
        channel.start_consuming()
        response = {"Topic" : topic, "Message" : consumed_message}
    else:
        response = {"Topic" : topic, "Message" : ''}
        
    print("outside of consume")
    """
    
@app.route("/chats/remove", methods=['GET']) # remove a chat from users profile/data base --> delete 2 queues
@auth_required
def chat_remove():
    print("in chat remove")
    

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=80, debug=True)
    connection.close()
