import sys
import socket
import threading

def valid_username(username):

    for char in username:
        validity = ((ord(char) - 48 >=0) and (ord(char)-48<10)) or ((ord(char) - 65>=0) and (ord(char) - 122<=0))
        if not validity:
            return False
    return True


class Server:
    def __init__(self,port_num):
        self.start_server(port_num)

    def start_server(self,port_num):
        self.sok = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        
        host = socket.gethostbyname(socket.gethostname())
        port = port_num

        self.clientsS = []
        self.clientsR = []

        self.sok.bind((host,port))
        self.sok.listen(100)                        #Total clients possible are 100
    
        print('Running server on host: '+str(host))
        print('Running server on port: '+str(port))

        self.username_lookupS = {}
        self.socket_lookupS = {}

        self.username_lookupR = {}
        self.socket_lookupR = {}

        while True:
            c, addr = self.sok.accept()

            username = c.recv(1024).decode()

            if(("REGISTER TOSEND " in username) and ('\n\n' in username) and (username[16:(len(username)-2)] in self.socket_lookupR.keys())):
                last_two = username[(len(username)-2):len(username)]
                username = username[16:(len(username)-2)]

                if(valid_username(username) and last_two=="\n\n"):
                    print('New sender connection. Username: '+str(username))

                    self.username_lookupS[c] = username
                    self.socket_lookupS[username] = c

                    self.clientsS.append(c)
                    c.send(("REGISTERED TOSEND "+username+"\n\n").encode())

                    threading.Thread(target=self.handle_client,args=(c,addr,)).start()
                else:
                    error_message = 'ERROR 100 Malformed username\n\n'
                    c.send(error_message.encode())
                
            elif("REGISTER TORECV " in username and '\n\n' in username):
                last_two = username[(len(username)-2):len(username)]
                username = username[16:(len(username)-2)]

                if(valid_username(username)  and last_two=="\n\n"):
                    print('New reciever connection. Username: '+str(username))

                    self.username_lookupR[c] = username
                    self.socket_lookupR[username] = c

                    self.clientsR.append(c)
                    c.send(("REGISTERED TORECV "+username+"\n\n").encode())

                else:
                    error_message = 'ERROR 100 Malformed username\n\n'
                    c.send(error_message.encode())

            else:
                print('Illegal registration request...')
                error_message = "ERROR 101 No user registered\n\n"
                c.send((error_message).encode())

    def checkMessageValdity(self,message):
        if message[0:5] != "SEND ":
            return False

        message = message[5:]
        reciever = ""

        for char in message:
            if char=='\n':
                break
            reciever = reciever + char

        if message[len(reciever):(len(reciever)+16)]!= "\nContent-length:":
            return False

        message = message[(len(reciever)+16):]
        len_message = ""

        validity = True

        for char in message:
            if char=='\n':
                break
            validity = ((ord(char) - 48 >=0) and (ord(char)-48<10))
            if not validity:
                break
            len_message = len_message + char

        if reciever=="" or len_message=="" or (not validity):
            return False

        len_int = int(len_message,10)

        if message[len(len_message):(len(len_message)+2)] != '\n\n':
            return False

        message = message[(len(len_message)+2):]

        if len(message)!= len_int:
            return False

        return True


    def handle_client(self,c,addr):
        thread_inprogress = True

        while thread_inprogress:
            try:
                msg = c.recv(1024)
            except:
                c.shutdown(socket.SHUT_RDWR)          
                print(str(self.username_lookupS[c])+' left the room.')
                break

            if msg.decode() != '':
                message = msg.decode()

                if (not self.checkMessageValdity(message)):
                    c.send(("ERROR 103 Header Incomplete\n\n").encode())

                    thread_inprogress = False
                    illegal_username = self.username_lookupS[c]
                    print('Deleting username : '+illegal_username+ ' from the chatroom')
                    self.username_lookupS.pop(c)
                    self.socket_lookupS.pop(illegal_username)
                    self.username_lookupR.pop(self.socket_lookupR[illegal_username])
                    c.close()
                    self.socket_lookupR[illegal_username].close()
                    self.socket_lookupR.pop(illegal_username)
                    continue

                message = message[5:]

                rec_username = ""
                for char in message:
                    if char=='\n':
                        break
                    rec_username = rec_username + char

                if (rec_username not in (self.socket_lookupS.keys()) and rec_username!="all"):
                    c.send(("ERROR 102 Unable to send\n\n").encode())
                    continue

                message = "FORWARD "+ self.username_lookupS[c] +message[len(rec_username):]

                if rec_username!="all":
                    self.socket_lookupR[rec_username].send(message.encode())

                    while True:
                        ack_message = (self.socket_lookupR[rec_username].recv(1024)).decode()

                        if ack_message!="":

                            if "ERROR " in ack_message:
                                error_message = "ERROR 102 Unable to send\n\n"
                                c.send(error_message.encode())
                                break
                            else:
                                ack_message = "SEND "+ rec_username+"\n\n"
                                c.send(ack_message.encode())
                                break
                else:
                    broadcast_failed = False

                    for allusername in self.socket_lookupS.keys():
                        if allusername!=self.username_lookupS[c]:

                            self.socket_lookupR[allusername].send(message.encode())

                            while True:
                                ack_message = (self.socket_lookupR[allusername].recv(1024)).decode()

                                if ack_message!="":

                                    if "ERROR " in ack_message:
                                        broadcast_failed = True
                                    
                                    break
                    
                    if broadcast_failed:
                        ack_message = "ERROR 102 Unable to send\n\n"
                        c.send(ack_message.encode())
                    else:
                        ack_message = "SEND all\n\n"
                        c.send(ack_message.encode())

if (len(sys.argv)!=2):
    print('Kindly please correctly enter the port number')
    sys.exit()

server = Server(int(sys.argv[1]))