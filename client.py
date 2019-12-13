import sys
import requests
import datetime
from getpass import getpass
import json
from geolocation.main import GoogleMaps
import subprocess



# Mac address
a = subprocess.check_output(["arp | awk '{print $1,$3}'"], shell = True)
macs = []
for i in a.split(b'\n')[:-1]:
    macs.append((i.split()[1]).decode("utf-8"))

del macs[0]
# Use two or more mac addresses to determine latitude and longitude
wifiaccesspoints = []
for i in macs:
    wifiaccesspoints.append({'macAddress': i})

gmaps_API_KEY = "AIzaSyA4SQw4hka-fjyTul9YQWdyGdEtPmO3DZA"

url = "https://www.googleapis.com/geolocation/v1/geolocate?key=" + gmaps_API_KEY
payload = {"considerIp": "true", 
            "wifiAccessPoints": wifiaccesspoints}
headers = {'content-type': 'application/json', 'Accept-Charset': 'UTF-8'}
r = requests.post(url, data=json.dumps(payload), headers=headers)

#From the lat and lng find the actual address
location = r.json()['location']
base = "https://maps.googleapis.com/maps/api/geocode/json?"
params = "latlng={lat},{lon}&key={key}&result_type=administrative_area_level_1|locality".format(
    lat=location['lat'],
    lon=location['lng'],
    key=gmaps_API_KEY
)
url = "{base}{params}".format(base=base, params=params)
r = requests.get(url)
city = (r.json())['results'][0]['address_components'][0]['short_name']
state = (r.json())['results'][1]['address_components'][0]['short_name']


status = ""



if len(sys.argv) != 3 or sys.argv[1] != '-s':
    #server_ip = "172.29.15.117"
    server_ip = "192.168.1.137"
else:
    server_ip = str(sys.argv[2])
    

def displayMenu():
    print("Welcome to your community's social network!\n")
    status = input("Are you a registered user? y/n? Press q to quit: ") 
    if status == "y":
        oldLogin()
    elif status == "n":
        newLogin()
    return status

def newLogin():
    global server_ip
    print("\nEnter 'q' in any of the fields to go back.")
    newUser = input("Create login name: ")
    if newUser == 'q':
        print("\nReturning to main menu...\n")
        return newUser  #Return anything to go back, has to be something
        
    r = requests.get("http://" + server_ip + "/newUser?username=" + newUser)
    
    while (r.json())['status'] == False: # check if login name exists
        print("\nLogin name already exist!\n")
        newUser = input("Create login name: ")
        r = requests.get("http://" + server_ip + "/newUser?username=" + newUser)
    
    #User has found an available username! Now add password to create account.
    newPass = getpass("Create password: ")
    
    #Encrypt password before sending
    
    
    r = requests.get("http://" + server_ip + "/newUser?username=" + newUser + "&password=" + newPass)
    print("\nUser created!\n")     

def oldLogin():
    print("\nEnter 'q' as login name to go back.")
    username = input("Enter login name: ")
    if username == 'q':
        return username #Return anything to go back, has to be something
    
    password = getpass("Enter password: ")

    # check if user exists and login matches password
    r = requests.get("http://" + server_ip + "/login?username=" + username + "&password=" + password)
    
    while (r.json())['status'] == False:
        print("\nUser doesn't exist or wrong password!\n")
        print("Enter 'q' to go back or try again.")
        username = input("Enter login name: ")
        if username == 'q':
            return username #Return anything to go back, has to be something
        password = getpass("Enter password: ")
        r = requests.get("http://" + server_ip + "/login?username=" + username + "&password=" + password)
    else:
        print("\nLogin successful!\n")
        loggedIn(username)

# On this screen user has many actions they can do.

def loggedIn(username):
    print("Printing user's subscribed topics and private chats!")
    print("p:<topic/friend>:\"<message/file>\" - Send messages/files to topic/friend queues.")
    print("c:<topic/friend> - Consume messages from topic/friend queues.")
    print("s:<topic> - Subscribes to a new topic.")
    print("u:<topic> - Unsubscribes to a topic.")
    print("a:<friend> - Adds a new friend and creates a private queue between you too.")
    print("d:<friend> - Deletes a friend and the associated private queue.\n")
    
    action = ""
    while action != "q":
        r = requests.get("http://" + server_ip + "/list?username=" + username)
        if (r.json())['status'] == True:
            topics = (r.json())['topics']
            friends = (r.json())['friends']
            print(topics)
            print(friends)
        else:
            print("Failed to fetch lists")
        action = input("What would you like to do?\n")
        splitlist = action.split(':')
        action = splitlist[0]
        tf = splitlist[1]
        print(action)
        print(tf)
        if len(splitlist) > 2:
            message = splitlist[2]
            print(message)
            r = requests.get("http://" + server_ip + "/produce?username=" + username)
        else:
            r = action(action)
                    
def action(i):
    switcher={
        'c': requests.get("http://" + server_ip + "/consume?username=" + username),
        's': requests.get("http://" + server_ip + "/subscribe?username=" + username),
        'u': requests.get("http://" + server_ip + "/unsubscribe?username=" + username),
        'a': requests.get("http://" + server_ip + "/add?username=" + username),
        'd': requests.get("http://" + server_ip + "/delete?username=" + username)
    }
    return switcher.get(i, "Invalid Action!")
            

while status != "q":            
    status = displayMenu()
