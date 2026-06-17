#ifndef PIDSEARCH_H
#define PIDSEARCH_H

#include <sys/socket.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <netdb.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <errno.h>
#include <arpa/inet.h>

#include <sys/time.h>
#include <time.h>

// Локальные (на каждый translation unit) данные (127.0.0.1 = приёмник на этой же машине)
static const char *IP = "127.0.0.1";
static const int   PORT = 17176;
static int         socketfd = 0;
static char        currentTime[84] = "";

// Макрос, который вставляет анализатор
#ifndef SENSOR
#define SENSOR(ID) sensor((ID))
#endif

inline char *get_time_with_ms() {
    struct timeval curTime;
    gettimeofday(&curTime, NULL);
    int milli = curTime.tv_usec / 1000;

    char buffer[80];
    strftime(buffer, 80, "%Y-%m-%d %H:%M:%S", localtime(&curTime.tv_sec));

    sprintf(currentTime, "%s.%03d+03:00", buffer, milli);
    return currentTime;
}

inline int open_socket() {
    int sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0)
        return -1;

    struct sockaddr_in serv_addr;
    memset(&serv_addr, 0, sizeof(serv_addr));
    serv_addr.sin_family = AF_INET;
    serv_addr.sin_port = htons(PORT);

    if (inet_pton(AF_INET, IP, &serv_addr.sin_addr) <= 0) {
        close(sockfd);
        return -1;
    }

    if (connect(sockfd, (struct sockaddr *)&serv_addr, sizeof(serv_addr)) < 0) {
        close(sockfd);
        return -1;
    }
    return sockfd;
}

inline void send_msg(const char *message) {
    if (socketfd <= 0) {
        socketfd = open_socket();
        if (socketfd <= 0)
            return;
    }
    if (message && strlen(message) > 0)
        write(socketfd, message, strlen(message));
}

inline void sensor(int id) {
    char message[255];
    sprintf(
        &message[0],
        "INSERT INTO ccc_sensoragramma (id, pid, parent_id, time) "
        "VALUES ('%d', '%d', '%d', '%s');\n",
        id, getpid(), getppid(), get_time_with_ms()
    );
    send_msg((const char *)message);
}

#endif // PIDSEARCH_H
