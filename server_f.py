import sys
import pika
import pymongo
import json
import signal
import time
from flask import Flask, request, make_response

app = Flask(__name__)
db = pymongo.MongoClient().users # initalize mongoDB database if not up
"""
def auth_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        
        if auth:
            result = db.userData.find_one({"username" : auth.username})
            if result != None:
                
                if result['password'] == auth.password:
                    return f(*args, **kwargs)
                
                return make_response('Invalid password', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
                
            return make_response('User:' + auth.username + ' does not exist', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})
            
        return make_response('Could not verify your login!', 401, {'WWW-Authenticate': 'Basic realm="Login Required"'})

    return decorated
"""
@app.route('/newUser')
def newUser():
	print("Attempting new account creation...")
	try:
		newUser = request.args.get('username')
		newPass = request.args.get('password')

		if newPass == None:	#Check if username is available
			result = db.userData.find_one({'username': newUser}, {'_id': 0, 'username': 1} )
			print("Verify if username is available")
			
			if result == None:
				print("Username available!")
				return json.dumps({'status': True})
			else:
				print("Username unavailable!")
				return json.dumps({'status': False})
		#Username is available, insert
		print("Adding new user to the databse!")	
		
		#insert new account into users mongodb
		db.userData.insert({'username': newUser, 'password': newPass, 'topics': [], 'friends': []})
		
	except:
		response = "There was an error"
        
	return json.dumps({'status': False})
	
@app.route('/login')
def login():
	print("Attempting login...")
	try:
		username = request.args.get('username')
		password = request.args.get('password')
		if username == None or password == None:
			return json.dumps({'status': False})
		else:
			result = db.userData.find_one({'username': username, 'password': password}, {'_id': 0, 'username': 1, 'password': 1} )
			print("Verify if username and password match")
			
			if result == None:
				print("Login failed!")
				return json.dumps({'status': False})
			else:
				print("Login successful!")
				return json.dumps({'status': True})
	except:
		response = "There was an error"
		
	return json.dumps({'status': False})
	
@app.route('/list')
#@auth_required
def list():
	print("Fetching user's personalized/private topics...")
	try:
		username = request.args.get('username')
		if username == None:
			return json.dumps({'status': False})
		else:
			result = db.userData.find_one({'username': username}, {'_id': 0, 'username': 1, 'topics': 1, 'friends': 1})
			
			if result == None:
				print("Fail!")
				return json.dumps({'status': False})
			else:
				print("Success")
				return json.dumps({'status': True, 'topics': result['topics'], 'friends': result['friends']})
	except:
		response = "There was an error"
		
	return json.dumps({'status': False})
	
@app.route('/produce')
#@auth_required
def produce():
	return "producing"

@app.route('/consume')
#@auth_required
def consume():
	return "consuming"
	
@app.route('/subscribe')
#@auth_required
def subscribe():
	return "subscribing"
	
@app.route('/unsubscribe')
#@auth_required
def unsubscribe():
	return "unsubscribing"
	
@app.route('/add')
#@auth_required
def add():
	return "adding"

@app.route('/delete')
#@auth_required
def delete():
	return "deleting"

				
if __name__ == "__main__":    
	app.run(host='0.0.0.0', port=80, debug=True)
