from socket import *
import sys
import re
import os

if len(sys.argv) <= 1:
    print('Usage : "python ProxyServer.py server_ip"\n[server_ip : It is the IP Address Of Proxy Server')
    sys.exit(2)

# Create a server socket, bind it to a port and start listening
tcpSerSock = socket(AF_INET, SOCK_STREAM)

tcpSerSock.bind((sys.argv[1], 8888))   # Bind to the IP and port 8888
tcpSerSock.listen(5)                   # Listen for up to 5 connections

while 1:
    # Start receiving data from the client
    print('Ready to serve...')
    tcpCliSock, addr = tcpSerSock.accept()
    print('Received a connection from:', addr)

    message = tcpCliSock.recv(4096).decode()     # Receive up to 4096 bytes, decode to string

    print(message)
    try:
        # Extract the URL from the GET line
        url = message.split()[1]
        match = re.match(r'http://([^/]+)(/.*)?', url)
        if match:
            hostname = match.group(1)
            path = match.group(2) or '/'
        else:
            # fallback: treat everything as hostname, no path
            hostname = url
            path = '/'

        # Safe cache filename: replace slashes with underscores
        cache_filename = hostname + path.replace('/', '_')
        print('Parsed hostname:', hostname)
        print('Parsed path:', path)
        print('Cache filename:', cache_filename)
    except Exception as e:
        print("Failed to parse request:", e)
        tcpCliSock.close()
        continue

    fileExist = "false"

    try:
        # Check whether the file exists in the cache
        f = open(cache_filename, "rb")   # Open as binary for generality
        outputdata = f.read()
        fileExist = "true"

        # ProxyServer finds a cache hit and generates a response message
        tcpCliSock.sendall(b"HTTP/1.0 200 OK\r\n")
        tcpCliSock.sendall(b"Content-Type:text/html\r\n\r\n")
        tcpCliSock.sendall(outputdata)
        print('Read from cache')

    # Error handling for file not found in cache
    except IOError:
        if fileExist == "false":
            try:
                # Create a socket on the proxyserver
                c = socket(AF_INET, SOCK_STREAM)
                print("Connecting to host:", hostname)
                c.connect((hostname, 80))

                # Send a correct HTTP/1.0 GET request to the remote server
                request_line = f"GET {path} HTTP/1.0\r\nHost: {hostname}\r\n\r\n"
                c.sendall(request_line.encode())

                # Receive the response from the remote server and cache it
                response = b""
                while True:
                    data = c.recv(4096)
                    if not data:
                        break
                    response += data

                # Save to cache
                with open(cache_filename, "wb") as tmpFile:
                    tmpFile.write(response)

                # Send to client
                tcpCliSock.sendall(response)

                c.close()
            except Exception as e:
                print("Illegal request or failed to connect:", e)
                tcpCliSock.send(b"HTTP/1.0 502 Bad Gateway\r\n\r\n")
        else:
            # HTTP response message for file not found
            tcpCliSock.sendall(b"HTTP/1.0 404 Not Found\r\nContent-Type:text/html\r\n\r\n")

    # Close the client socket
    tcpCliSock.close()
