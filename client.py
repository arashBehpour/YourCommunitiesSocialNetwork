import sys
import pika
import pymongo
import json
import signal
import time

def parser(words):
	action = ''
	place = ''
	subject = ''
	message = ''
	
	splitList = words.split(':')
    
	if len(splitList) > 1:
		action = splitList[0]
		splitList = splitList[1].split('+')
		
		if len(splitList) > 1:
			place = splitList[0]
			splitList = splitList[1].split('"')
			
			if len(splitList) > 0:
				subject = splitList[0]
			
			if len(splitList) > 1:
				message = splitList[1]
				
	action.strip()
	place.strip()
	subject = "".join(subject.split())
	subject.strip()
	message.strip()
	return action, place, subject, message; # returning a tuple

if len(sys.argv) != 3 or sys.argv[1] != '-s':
	print("Arguments inputed: ", str(sys.argv))
	print("Format: client.py -u <username>")    # -u is optional, client.py should ask for username and password upon starting
	sys.exit()

repository_ip = str(sys.argv[2])

db = pymongo.MongoClient().test # initalize mongoDB database if not up

# Initalize RabbitMQ Service(exchanges/queues/bindings) on repository rpi
rabbitmq_user = "admin" #Change these based on user input
rabbitmq_pass = "admin" 

credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)
connection = pika.BlockingConnection(pika.ConnectionParameters(repository_ip, 5672, '/', credentials)) # Orig = 'localhost'
channel = connection.channel()

# Declare Exchanges
channel.exchange_declare(exchange='Blacksburg', exchange_type='direct')
channel.exchange_declare(exchange='Christiansburg', exchange_type='direct')
channel.exchange_declare(exchange='Roanoke', exchange_type='direct')

#Declare Queues
foodQueue = channel.queue_declare(queue='Food')
videoGamesQueue = channel.queue_declare(queue='Video Games')
mmaQueue = channel.queue_declare(queue='MMA')
classroomsQueue = channel.queue_declare(queue='Classrooms')
auditoriumQueue = channel.queue_declare(queue='Auditorium')
noiseQueue = channel.queue_declare(queue='Noise')
seatingQueue = channel.queue_declare(queue='Seating')
wishesQueue = channel.queue_declare(queue='Wishes')

# Binding's
channel.queue_bind(exchange='Blacksburg', queue='Food', routing_key='Food')
channel.queue_bind(exchange='Blacksburg', queue='Video Games', routing_key='Video Games')
channel.queue_bind(exchange='Blacksburg', queue='MMA', routing_key='MMA')
channel.queue_bind(exchange='Christiansburg', queue='Classrooms', routing_key='Classrooms')
channel.queue_bind(exchange='Christiansburg', queue='Auditorium', routing_key='Auditorium')
channel.queue_bind(exchange='Roanoke', queue='Noise', routing_key='Noise')
channel.queue_bind(exchange='Roanoke', queue='Seating', routing_key='Seating')
channel.queue_bind(exchange='Roanoke', queue='Wishes', routing_key='Wishes')

#Declare dictionary to use to decide when to stop consuming
queuesMap = {
	"Food": foodQueue.method.message_count,
	"Video Games": videoGamesQueue.method.message_count,
	"MMA": mmaQueue.method.message_count,
	"Classrooms": classroomsQueue.method.message_count,
	"Auditorium": auditoriumQueue.method.message_count,
	"Noise": noiseQueue.method.message_count,
	"Seating": seatingQueue.method.message_count,
	"Wishes": wishesQueue.method.message_count
}


try:
	while True:
		try:
			data = client_sock.recv(1024)
		except KeyboardInterrupt:
			break
		
		if data: 
			# Display produce/consume messages
			print(time.strftime('[%H:%M:%S]'), "[Checkpoint 01] Message captured:", data)
			
			# Produce/Consume messages through bluetooth RFcomm, GPIO: red= produce request, green= consume request
			# p:exchange+queue message OR c:exchange+queue
			action, place, subject, message = parser(data.decode())  
			
			if place == '' or subject == '' or (not (action == 'p' or action == 'c')):
				print("Incorrect format!")
				print("Correct Format> p:place+subject message OR c:place+subject")
				continue
			
			# MongoDB insert messages into persistent database
			new_msg = { "Action": action, "Place": place, "MsgID": "01$%.f" % time.time(), "Subject": subject, "Message": message }
			print(time.strftime('[%H:%M:%S]'), "[Checkpoint 02] Store command in MongoDB instance:", new_msg)
			db.utilization.insert(new_msg)
									
			if action == 'p': # Produce /consume command to repository rpi through rabbitMQ --> Direct Exchange
				channel.basic_publish(exchange=place, routing_key=subject, body=message)
				
				print(time.strftime('[%H:%M:%S]'), "[Checkpoint 04] Print out RabbitMQ command sent to the Repository RPi: Produce")
				print("[x] Sent %r:%r" % (subject, message))
				
				queuesMap[subject] = queuesMap[subject] + 1
				
				print(time.strftime('[%H:%M:%S]'), "[Checkpoint 05] Nothing generated/received by RabbitMQ:" )
				
			elif action == 'c':
				print(time.strftime('[%H:%M:%S]'), "[Checkpoint 04] Print out RabbitMQ command sent to the Repository RPi: Consume")
				
				def callback(ch, method, properties, body):
					print("%r:%r" % (method.routing_key, body)) #Display recieved/consumed message
					queuesMap[subject] = queuesMap[subject] - 1
					if queuesMap[subject] <= 0:
						channel.stop_consuming() #Stop consuming
						
				if queuesMap[subject] != 0:
					channel.basic_consume(callback, queue=subject, no_ack=True)
					print(time.strftime('[%H:%M:%S]'), "[Checkpoint 05] Bridge RPi prints statements generated by RabbitMQ:" )
					channel.start_consuming()
				else:
					print(time.strftime('[%H:%M:%S]'), "[Checkpoint 05] Nothing in the RabbitMQ's queue to consume.")
					
			
except IOError:
	pass
		
		
print("Closing Connections")

connection.close()				
print("Finished")
