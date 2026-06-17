/*
Вставлять датчик в таком виде sensor(id, getpid() ...);
*/
#include <unistd.h>
#include <string>
#include <sstream>
#include <syslog.h>

#include <stdio.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <netdb.h>
#include <cstring>

#include <ctime>
#include <iostream>
#include <chrono>

template <typename T>
std::string toString(T val){
    std::ostringstream oss;
    oss<< val;
    return oss.str();
}

//FROM
//012345678901234567890123
//Thu Jul  9 16:03:47 2020
//TO
//2020-07-09 15:15:27.852244+03:00
std::string convert(const char * t, int ms){
  std::string result = toString(t[20]) + toString(t[21]) + toString(t[22]) + toString(t[23]) + toString("-");
  switch (t[4]) {
    case 'J':
      if(t[5] == 'a')
        result += toString("01-");
      else if(t[6] == 'n')
        result += toString("06-");
      else
        result += toString("07-");
      break;
    case 'F':
      result += toString("02-");
      break;
    case 'M':
      if(t[6] == 'r')
        result += toString("03-");
      else
        result += toString("05-");
      break;
    case 'A':
      if(t[5] == 'p')
        result += toString("04-");
      else
        result += toString("08-");
      break;
    case 'S':
      result += toString("09-");
      break;
    case 'O':
      result += toString("10-");
      break;
    case 'N':
      result += toString("11-");
      break;
    case 'D':
      result += toString("12-");
      break;
  };
  if (' ' == t[8])
    result += toString("0");
  else
    result += toString(t[8]);
  result += toString(t[9]) + toString(" ");
  for(int i = 11; i < 19; i++)
    result += toString(t[i]);
  result += toString(".") + toString(ms % 1000) + toString("+03:00");
  return result;
}

std::string getTime()
{
  using namespace std::chrono;

  milliseconds ms = duration_cast< milliseconds >(system_clock::now().time_since_epoch());

  std::time_t result = std::time(nullptr);
  return convert(std::asctime(std::localtime(&(result))), ms.count());
}

const char * IP = "192.168.0.42";
const char * PORT = "514";

void error(const char *msg)
{
    perror(msg);
    exit(0);
}



int send(const char* message)
{
    int sockfd, portno, n;
    struct sockaddr_in serv_addr;
    struct hostent *server;

    char buffer[256];

    portno = atoi(PORT);
    sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0)
        error("ERROR opening socket");
    server = gethostbyname(IP);
    if (server == NULL) {
        fprintf(stderr,"ERROR, no such host\n");
        exit(0);
    }
    bzero((char *) &serv_addr, sizeof(serv_addr));
    serv_addr.sin_family = AF_INET;
    bcopy((char *)server->h_addr,
         (char *)&serv_addr.sin_addr.s_addr,
         server->h_length);
    serv_addr.sin_port = htons(portno);
    if (connect(sockfd,(struct sockaddr *) &serv_addr,sizeof(serv_addr)) < 0)
        error("ERROR connecting");
    // printf("Please enter the message: ");
    // bzero(buffer,256);
    // fgets(buffer,255,stdin);
    n = write(sockfd, message,strlen(message));
    if (n < 0)
         error("ERROR writing to socket");
    // bzero(buffer,256);
    // n = read(sockfd,buffer,255);
    // if (n < 0)
    //      error("ERROR reading from socket");
    // printf("%s\n",buffer);
    close(sockfd);
    return 0;
}

void sensor(int id, pid_t pid, int parent_id){
  std::string sql = "INSERT INTO ccc_sensoragramma (id, pid, parent_id, time) VALUES ('" + toString(id) + "', '" + toString(pid) + "', '" + toString(parent_id) + "', '" + getTime() + "');";
  const char * c = sql.c_str();
  // cout << c;
  send(c);
}

// int main() {
//   for(int i = 0; i < 30000; i++)
//     sensor(i, 0, "test", 0, 0);
//   return 0;
// }
