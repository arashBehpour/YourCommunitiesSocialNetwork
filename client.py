import sys
import requests
import os
from requests.auth import HTTPDigestAuth
import datetime
from getpass import getpass
import json
from geolocation.main import GoogleMaps
import subprocess
import pyaudio
import wave
from ibm_watson import TextToSpeechV1, SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator
import pygame

#IBM KEYSSS
authenticator = IAMAuthenticator('a7GSf5ZOhnjfAvu-5bS2qVMwE2OMR3hSPOgSUzRmuZ6V')
text_to_speech_service = TextToSpeechV1(
    authenticator=authenticator,
)
text_to_speech_service.set_service_url('https://gateway-wdc.watsonplatform.net/text-to-speech/api')

authenticator1 = IAMAuthenticator('NFwUeOyzBKotv0SMydyzlvCzvVeqFd3B9QzoYgeCEnzr')
speech_to_text_service = SpeechToTextV1(
    authenticator=authenticator1
)
speech_to_text_service.set_service_url('https://stream.watsonplatform.net/speech-to-text/api')

# Mac address
a = subprocess.check_output(["arp | awk '{print $1,$3}'"], shell = True)
macs = []
for i in a.split(b'\n')[:-1]:
    macs.append((i.split()[1]).decode("utf-8"))

del macs[0]
# Use two or more mac addresses to determine latitude and longitude or revert to ip
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

#Combine state and city to form final location
location = state + '-' + city.lower()
status = ""



if len(sys.argv) != 3 or sys.argv[1] != '-s':
    print("Arguments inputed: ", str(sys.argv))
    print("Format: client.py -s <server_IP>")
    sys.exit()
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
    
    newPass = getpass("Create password: ")
    confirmPass = getpass("Confirm password: ")
    while (newPass != confirmPass):
        print("Passwords do not match try again")
        newPass = getpass("Create password: ")
        confirmPass = getpass("Confirm password: ")

    r = requests.get("http://" + server_ip + "/create/user?username=" + newUser + "&password=" + newPass)
    print(r.json())
    while 'Error' in r.json(): # check if login name exists
        print(r.json()['Error'])
        newUser = input("Create login name: ")
        newPass = getpass("Create password: ")
        confirmPass = getpass("Confirm password: ")
        while (newPass != confirmPass):
            print("Passwords do not match try again")
            newPass = getpass("Create password: ")
            confirmPass = getpass("Confirm password: ")
        r = requests.get("http://" + server_ip + "/create/user?username=" + newUser + "&password=" + newPass)
    
    print("\nUser " + newUser + " created!\n") 

def oldLogin():
    print("\nEnter 'q' as login name to go back.")
    username = input("Enter login name: ")
    if username == 'q':
        return username #Return anything to go back, has to be something
    
    password = getpass("Enter password: ")
    
    # Retrieve user lists to determine if user exists
    r = requests.get("http://" + server_ip + "/topics/list?loc=" + location + "&user=" + username, auth=(username, password))
    while r.status_code != 200:
        print("\nUser doesn't exist or wrong password!\n")
        print("Enter 'q' to go back or try again.")
        username = input("Enter login name: ")
        if username == 'q':
            return username #Return anything to go back, has to be something
        password = getpass("Enter password: ")
        r = requests.get("http://" + server_ip + "/topics/list?loc=" + location + "&user=" + username, auth=(username, password))
    print("\nLogin successful!\n")
    auth=(username, password)
    loggedIn(auth)

# On this screen user has many actions they can do.

def loggedIn(auth):
    
    print("Available Actions:")
    print("p:topic - Send messages/files to topics.") # This needs to change to a post request
    print("c:topic - Receive messages from topics.")
    print("l:topic - List local topics.")
    print("u:topic - Unsubscribes to a topic.\n")
    print("l:chat - Lists user's chats.")
    print("a:chat - Adds a new friend and creates two private queues between you two.")
    print("p:chat - Sends messages to a friend in your list.") # This needs to change to a post request
    print("c:chat - Receives messages from a friend of your choice.")
    print("r:chat - Removes a friend and the associated private queue.")
    print("q - LOGOUT\n")
    
    r = requests.get("http://" + server_ip + "/topics/list?loc=" + location + "&user=" + auth[0], auth=auth)
    print("Subscribed Topics: ")
    for t in r.json()['Topics']:
        print(t)
    
    action = ""
    
    while action != 'q':
        action = input("What would you like to do?\n")
        splitlist = action.split(':')
        action = splitlist[0]
        if action == 'q':
            return action
        elif len(splitlist) == 1:
            print("Invalid action!\n")
        elif len(splitlist) == 0 or len(splitlist) > 2:
            print("Invalid number of arguments!\n")
        else:
            tc = splitlist[1]
            if tc == "topic":
                print(topic(action, auth))
            elif tc == "chat":
                print(chat(action, auth))
            else:
                print("Cmon now, give me a valid input you benchod!")
        
    return action
                    
def topic(i, auth):
    if i == 'p': 
        voice = input("Would you like to send a text/voice message? t/v? ")
        if voice == 't':
            anonymous = input("Would you like to speak your text into existence? y/n? ")
            if anonymous == 'y':
                sec = input("How many seconds would you like to record for (0<s<121)? ")
                while int(sec) <= 0 or int(sec) > 120:
                    sec = input("Outside of range! Try again.. (0<s<121)? ")
                record(sec, auth)
                return "Converted from speech to text!"
            elif anonymous == 'n':
                topic = input("What is the topic name? ")
                message = input("What is your message? ")
                r = requests.post("http://" + server_ip + "/topics/produce?mssg=" + message + "&loc=" + location + "&topic=" + topic, auth=auth)
                return r.json()
        elif voice == 'v':
            message = input("What is your message? ")
            topic = input("Which topic? ")
            r = requests.post("http://" + server_ip + "/topics/produce?mssg=" + message + "&loc=" + location + "&topic=" + topic + "&isAnonymous=True", auth=auth)
            return
    elif i == 'c':
        r = requests.get("http://" + server_ip + "/topics/consume?loc=" + location + "&topic=" + input("Which topic would you like to consume from?"), auth=auth)
        if 'isAudio' in r.json():
            download_file_from_server_endpoint(r)
        elif 'isAnonymous' in r.json():
            # Add IBM TTS code or function here
            with open("anonymous.mp3", 'wb') as audio_file:
                response = text_to_speech_service.synthesize(r.json()['Message'],
                                                             accept='audio/mp3',
                                                             voice="en-US_AllisonVoice").get_result()
                audio_file.write(response.content)

            # Plays answer audio
            #pygame.mixer.init()
            #pygame.mixer.music.load("anonymous.mp3")
            #pygame.mixer.music.play()
            
        return r.json()
    elif i == 'l': 
        list_type = input("Would you like to retrieve 'local' lists or your 'user' list again? ")
        if list_type == "local":
            r = requests.get("http://" + server_ip + "/topics/list?loc=" + location, auth=auth)
            return r.json()
        elif list_type == "user":
            r = requests.get("http://" + server_ip + "/topics/list?loc=" + location + "&user=" + auth[0], auth=auth)
            return r.json()
    elif i == 'u': 
        r = requests.get("http://" + server_ip + "/topics/unsubscribe?topic=" + input("Which topic would you like to unsubscribe from? "), auth=auth)
        return r.json()
    else: 
        return "Invalid action!"

def chat(i, auth):
    if i == 'p': 
        friend = input("What is the friend's name? ")
        message = input("What is your message? ")
        r = requests.get("http://" + server_ip + "/chats/produce?chatUser=" + friend + "&mssg=" + message, auth=auth)
        return r.json()
    elif i == 'c':
        r = requests.get("http://" + server_ip + "/chats/consume?chatUser=" + input("Who's messages would you like to read? "), auth=auth)
        return r.json()
    elif i == 'l': 
        r = requests.get("http://" + server_ip + "/chats/list", auth=auth)
        return r.json()
    elif i == 'a': 
        r = requests.get("http://" + server_ip + "/chats/create?chatUser=" + input("Who would you like to add? "), auth=auth)
        return r.json()
    elif i == 'r':
        r = requests.get("http://" + server_ip + "/chats/remove?chatUser=" + input("Who would you like to remove? "), auth=auth)
        return r.json()
    else: 
        return "Invalid action!"
        
def record(sec, auth):
    #The following code comes from markjay4k as referenced below
    topic = input("What is the topic name? ")
    form_1 = pyaudio.paInt16
    chans=1
    samp_rate = 48000
    chunk = 4096
    record_secs = int(sec)    #record time
    dev_index = 2
    wave_output_filename = 'audio.wav'


    audio = pyaudio.PyAudio()

    #setup audio input stream
    stream=audio.open(format = form_1,rate=samp_rate,channels=chans, input_device_index = dev_index, input=True, frames_per_buffer=chunk)
    print("recording")
    frames=[]

    for ii in range(0,int((samp_rate/chunk)*record_secs)):
        data=stream.read(chunk,exception_on_overflow = False)
        frames.append(data)

    print("finished recording")

    stream.stop_stream()
    stream.close()
    audio.terminate()

    #creates wave file with audio read in
    #Code is from the wave file audio tutorial as referenced below
    wavefile=wave.open(wave_output_filename,'wb')
    wavefile.setnchannels(chans)
    wavefile.setsampwidth(audio.get_sample_size(form_1))
    wavefile.setframerate(samp_rate)
    wavefile.writeframes(b''.join(frames))
    wavefile.close()
    
    #IBM SPEECH TO TEXT
    message = ''
    jsonm= ''
    with open(wave_output_filename, 'rb') as audio_file:
        jsonm = speech_to_text_service.recognize(
            audio=audio_file, 
            content_type='audio/wav',
            timestamps=False, 
            word_confidence=False).get_result()
    message=jsonm['results'][0]['alternatives'][0]['transcript']
    print(message)
    
    response = requests.post("http://" + server_ip + "/topics/produce?mssg=" + message + "&loc=" + location + "&topic=" + topic, auth=auth)
    return response

    #send_data_to_server(wave_output_filename, auth)
    #files = [
    #    ("file", (wave_output_filename, open(wave_output_filename, "rb"), "wav"))
    #]
    
    #files = { 'file': open(wave_output_filename, 'rb')}
    
    #files = open(wave_output_filename, "rb") 
    #data = files.read()
    #print(data)
    #print(type(data))
    #response = requests.post("http://" + server_ip + "/topics/produce?mssg=file&loc=" + location + "&topic=" + topic + "&isAudio=True", files=files, auth=auth)
    #return response


def download_file_from_server_endpoint(response):
 
    # Send HTTP GET request to server and attempt to receive a response
    #response = requests.get(server_endpoint)
     
    # If the HTTP GET request can be served
    print(response.status_code)
    if response.status_code == 200:
        #print(response.iter_content)
        file_bytes = (response.json()['Message']).encode('UTF-8')
        # Write the file contents in the response to a file specified by local_file_path
        with open("receivedAudio.wav", 'wb') as local_file:
            #for chunk in file_bytes(chunk_size=128):
            local_file.write(file_bytes)
            

while status != "q":            
    status = displayMenu()
