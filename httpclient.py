#!/usr/bin/env python
# coding: utf-8
# Copyright 2015 Abram Hindle, Dylan Stankievech
#
# Code edited by Dylan Stankievech for the purposes of CMPUT410W15 Assignment 2
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Do not use urllib's HTTP GET and POST mechanisms.
# Write your own HTTP GET and POST
# The point is to understand what you have to send and get experience with it

import sys
import socket
import re
# you may use urllib to encode data appropriately
import urllib
from urlparse import urlparse

def help():
    print "httpclient.py [GET/POST] URL\n"

class HTTPRequest(object):
    def __init__(self, code=200, body=""):
        self.code = code
        self.body = body
        

class HTTPClient(object):

    # connect a web socket to the given host on the given port
    def connect(self, host, port):
        # sometimes host includes the port, remove it since port is a separate parameter
        host = re.sub('\:\d+$', '', host)
        try:
            # create socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error, msg:
            print 'Failed to create socket. Error code: ' + str(msg[0]) + ' , Error message : ' + msg[1]
            sys.exit();
 
        try:
            # find ip of host
            remote_ip = socket.gethostbyname( host )
        except socket.gaierror:
            print 'Hostname could not be resolved. Exiting'
            sys.exit()
 
        # set a timeout for this socket, in case server lies about content-length
        s.settimeout(3)

        # connect to host on given port
        s.connect((remote_ip , port))

        return s

    # send the given http request on the given socket, return the response
    def send_request(self, socket, request):
        try :
            socket.sendall(request)
        except socket.error:
            print 'Send failed'
            sys.exit()

        response = self.recvall(socket)

        return response
        
    # extract the http status code from a response
    def get_code(self, data):
        lines = data.split('\r\n')
        if (len(lines) > 0):
            # get the first line of the response
            tokens = lines[0].split()
            if (len(tokens) > 1):
                # the second token is the status code
                return int(tokens[1])
            else:
                return None
        else:
            return None

    # extract the headers of a http response
    def get_headers(self,data):
        sections = data.split('\r\n\r\n')
        headers = sections[0].split('\r\n')
        if (len(headers) > 1):
            # ignore the first line of the head
            return headers[1:]
        else:
            return None

    # extract the body of a http response
    def get_body(self, data):
        sections = data.split('\r\n\r\n')
        if (len(sections) > 1):
            # the body is the section after the \r\n\r\n
            return sections[1]
        else:
            return None

    # read everything from the socket
    def recvall(self, sock):
        buffer = bytearray()
        done = False
        while not done:
            # added a timeout in case any server lies or forgets the content-length
            try:
                part = sock.recv(4096)
            except socket.timeout:
                done = True
            
            if (part and not done):
                buffer.extend(part)
            else:
                done = True

            # check if we've read the entire response
            if (self.check_if_done(buffer)):
                done = True

        return str(buffer)

    # to check if we've read the full server response
    def check_if_done(self, data):
        lines = data.split('\r\n')
        data_length = 0
        has_header = False
        for line in lines:
            # find the header for content length if we've received it
            if (re.search(r'^Content-Length:\s*\d+$', line)):
                has_header = True
                # to get the content length
                data_length = int(re.search(r'\d+', line).group())
                break
        
        # sections[0] should be response and headers
        # sections[1] should be the body, ex: the html page
        sections = data.split('\r\n\r\n')

        if (len(sections) < 2):
            # haven't read the entire response yet
            return False

        if (has_header and len(sections[1]) == data_length):
            # if we've read as much as the server claims to have sent
            return True
        else:
            # we are not done reading yet
            return False

    # makes a get request to the given URL
    # returns an object of the response with a code and body
    def GET(self, url, args=None):
        query_string = ""

        # if we are passed any query arguments, need to encode them
        if (args):
            query_string = urllib.urlencode(args)

        # if the query string is not empty, add it to the URL
        if (query_string):
            url = url + "?" + query_string

        parsed = urlparse(url) # a parsed object
        path = urllib.quote(parsed.path) # the path for the request line
        host = urllib.quote(parsed.netloc, ':') # the host for the header
        query = urllib.quote(parsed.query) # the query arguments
        port = parsed.port # a possibly specified port

        # if no port specified, use port 80
        if (not port):
            port = 80        

        # if there were query arguments, add a question mark to append to path
        if (query):
            query = "?" + str(query)      

        # if path is missing, we'll request the server directory
        if (not path):
            path = "/"

        # the full GET request
        request = "GET " + path + query + " HTTP/1.1\r\nHost: " + host + "\r\n\r\n"  
        response = ""

        # connect to the host server
        s = self.connect(host, port)

        # send the request and get the response
        response = self.send_request(s, request)

        code = self.get_code(response)
        headers = self.get_headers(response)
        body = self.get_body(response)

        # close the port
        s.close()

        return HTTPRequest(code, body)

    #makes a post request to the given URL
    #returns an object of the response with a code and body
    def POST(self, url, args=None):
        query_string = ""
        
        # if we are passed any query arguments, need to encode them        
        if (args):
            query_string = urllib.urlencode(args)
   
        parsed = urlparse(url) # a parsed object
        path = urllib.quote(parsed.path) # the path for the request line
        host = urllib.quote(parsed.netloc, ':') # the host for the header
        port = parsed.port # a possibly specified port

        # if no port specified, use port 80
        if (not port):
            port = 80           

        # if path is missing, we'll request the server directory
        if (not path):
            path = "/"

        # the full POST request
        request = "POST " + path + " HTTP/1.1\r\nHost: " + host + "\r\n" + "Content-Length: " + str(len(query_string)) + "\r\nContent-Type: application/x-www-form-urlencoded\r\n\r\n" + query_string
        response = ""
        
        # connect to the host server
        s = self.connect(host, port)

        # send the request and get the response
        response = self.send_request(s, request)

        code = self.get_code(response)
        headers = self.get_headers(response)
        body = self.get_body(response)

        # close the port
        s.close()
        return HTTPRequest(code, body)

    def command(self, url, command="GET", args=None):
        if (command == "POST"):
            return self.POST( url, args ).body
        else:
            return self.GET( url, args ).body
        
    
if __name__ == "__main__":
    client = HTTPClient()
    command = "GET"
    if (len(sys.argv) <= 1):
        help()
        sys.exit(1)
    elif (len(sys.argv) == 3):
        print client.command( sys.argv[2], sys.argv[1] )
    else:
        print client.command( sys.argv[1], command  )    
