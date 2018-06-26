//#include <QCoreApplication>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <errno.h>
#include <iostream>
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
//#include <QString>
#include <stdio.h>
//#include <time.h>
#include <ctime>
//#include <string>
#include <curl/curl.h>
#include <thread>
#include <string>
#include <sstream>
#include <iomanip>
#include <fstream>

#define MAXBUFSIZE 1328 // Max UDP Packet size is 64 Kbyte //was 65536
#define PACKETS_TO_MAX_BUFFER 2000
//#define BYTES_TO_COPY 5
#define DUMP 0
#define DEFAULT_TS_PACKET_SIZE 188
#define DEFAULT_UPDATE_TIME 60
#define DEFAULT_SLEEP_TIME 5
#define CHECK_NO_DATA_USLEEP 1000000
#define RESPONSES_PER_DEFAULT_UPDATE_TIME 100





void help();
void checkCC(uint8_t *buffer, uint16_t *pid, int size);
void updateStreamStatusInDB(char *argv[], int key);
void copyToDumpBuffer();
void writeDumpAndClose();
uint16_t getPidFromTable(uint8_t *p_big_buffer, uint buffer_size, bool is_pmt_pid, uint16_t table_pid);
uint8_t *big_buffer = new uint8_t[MAXBUFSIZE*PACKETS_TO_MAX_BUFFER];
uint8_t *start_big_buffer = big_buffer;
uint maxBuffCounter = 0;
uint maxBuffSize = 0;
uint16_t pcr_pid = 0;
uint ccCounter = 0;
uint lostUdpPackagesCounter = 0;
int udpRaiseCounter = 0;
//int error_flag = 0;
int streamStatus = -1;
int bitrate = 0;
int bitrateOneSec = 0;
int fastBitrateOneSec = 0;
int sleepCounter = 0;
int notDDosCounter = RESPONSES_PER_DEFAULT_UPDATE_TIME;
bool justStart = 1;
//bool curlIsDiong = 0;

int8_t cc = -1;
int8_t ecc = -1;
bool ccErrorOccurcs = 0;
time_t lastErrorTime = time(NULL);
//uint8_t slidingArr[BYTES_TO_COPY] = {0};
int addressIndex, portIndex, idIndex, nameIndex, reportLinkIndex, minBitrateIndex;
CURL *curl;
// DUMP
//uint8_t dump_buffer_current[MAXBUFSIZE] = {0};
//uint8_t dump_buffer_old[MAXBUFSIZE] = {0};
//bool needToWriteDumpAndExit = 0;
uint8_t buffer[MAXBUFSIZE];
int needToUpdateStatus = 0;
//int errorByte = 0;

//scrambling control
int lastScrambled = -1;
int scrambled = -1;
int scrambledStatus = -1;

// Get current date/time, format is YYYY-MM-DD.HH:mm:ss
const std::string currentDateTime() {
    time_t     now = time(0);
    struct tm  tstruct;
    char       buf[80];
    tstruct = *localtime(&now);
    strftime(buf, sizeof(buf), "%Y-%m-%d.%X", &tstruct);

    return buf;
}

void create_hex_str(uint8_t *data, int len, std::string &tgt)
{
    std::stringstream ss;
    ss << std::hex << std::setfill('0');
    ss << "\n";
    for (int i=0; i<len; i++)
    {
        ss << std::setw(2) << static_cast<unsigned>(data[i]) << " ";
    }
    tgt = ss.str();
}

/*void sendStatusThread(char *argv[])
{
    time_t seconds1, seconds2, secondsDelta;
    while(1) {
        seconds1 = time(NULL);
        sleep(DEFAULT_SLEEP_TIME);
        ++sleepCounter;
        curl = curl_easy_init();
        std::string strRequestLink = std::string(argv[reportLinkIndex])+"?multicast=";
        strRequestLink += std::string(argv[addressIndex]);
        strRequestLink += "&id="+std::string(argv[idIndex])+"&name="+std::string(argv[nameIndex]);
        if (statusHasBeenChanged || sleepCounter >= DEFAULT_UPDATE_TIME/DEFAULT_SLEEP_TIME) {
            strRequestLink += "&status="+std::to_string(streamStatus);
            statusHasBeenChanged = 0;
        } else {
            strRequestLink +="&status=-1";
        }
        seconds2 = time(NULL);
        secondsDelta = seconds2 - seconds1;
        if (secondsDelta < 0) {
            secondsDelta = DEFAULT_SLEEP_TIME;
        }
        strRequestLink += "&secbitrate="+std::to_string(((bitrateOneSec*8)/1024)/secondsDelta);
        bitrateOneSec = 0;
        if (sleepCounter >= DEFAULT_UPDATE_TIME/DEFAULT_SLEEP_TIME) {
            strRequestLink += "&bitrate="+std::to_string((((bitrate/DEFAULT_UPDATE_TIME)*8)/1024));
            bitrate = 0;
            sleepCounter = 0;
        } else {
            strRequestLink +="&bitrate=0";
        }
        strRequestLink += "&cc="+std::to_string(ccCounter)+"&udp="+std::to_string(lostUdpPackagesCounter);
        strRequestLink +="&raise="+std::to_string(udpRaiseCounter);

        if (scrambledStatus != -1) {
            strRequestLink +="&scrambled="+std::to_string(scrambledStatus);
        } else {
            strRequestLink += "&scrambled=-1";
        }
        lostUdpPackagesCounter = 0;
        udpRaiseCounter = 0;
        ccCounter = 0;
        scrambledStatus = -1;
        curl_easy_setopt(curl, CURLOPT_URL, strRequestLink.c_str());
        curl_easy_perform(curl);
        curl_easy_cleanup(curl);
        std::cerr << strRequestLink << std::endl;
    }
}*/

void sendStatusThread(char *argv[])
{
    time_t seconds1, seconds2, secondsDelta;
    int noDataCounter;
    int previousFastStatus = -1, fastStatus = -1;
    while(1) {
        int local_status = -1;
        noDataCounter = DEFAULT_SLEEP_TIME*1000000/CHECK_NO_DATA_USLEEP;
        seconds1 = time(NULL);
        sleepCounter += DEFAULT_SLEEP_TIME*1000000;
        while(noDataCounter--) {
            usleep(CHECK_NO_DATA_USLEEP);
            // битрейт за секунду меньше порогового значения (CHECK_NO_DATA_USLEEP в данный момент 1 сек)
            if (fastBitrateOneSec < ((atoi(argv[minBitrateIndex])*1024)/8)) {
                fastStatus = 0;
                sleepCounter -= (((DEFAULT_SLEEP_TIME*1000000/CHECK_NO_DATA_USLEEP) - noDataCounter) * CHECK_NO_DATA_USLEEP);
                break;
            } else {
                fastStatus = 1;
            }
        }

        // сравниваем новый статус и предыдущий
        if (previousFastStatus == fastStatus || justStart) {
        // запоминаем текущий статус для следующей итерации статус
            previousFastStatus = fastStatus;
            // fastStatus обновлять не нужно если ничего не изменилось
            fastStatus = -1;
        } else {
            // запоминаем текущий статус для следующей итерации статус
            previousFastStatus = fastStatus;

        }

        seconds2 = time(NULL);
        secondsDelta = seconds2 - seconds1;
        if (secondsDelta <= 0) {
            secondsDelta = DEFAULT_SLEEP_TIME;
        }

        //sleepCounter += DEFAULT_SLEEP_TIME*1000000/CHECK_NO_DATA_USLEEP;
        //sleepCounter++;

        curl = curl_easy_init();
        std::string strRequestLink = std::string(argv[reportLinkIndex])+"?multicast=";
        strRequestLink += std::string(argv[addressIndex]);
        strRequestLink += "&id="+std::string(argv[idIndex])+"&name="+std::string(argv[nameIndex]);


        strRequestLink += "&secbitrate="+std::to_string(((bitrateOneSec*8)/1024)/secondsDelta);
        // пора обновлять минутный статус
        if (sleepCounter >= DEFAULT_UPDATE_TIME*1000000) {
            strRequestLink += "&bitrate="+std::to_string((((bitrate/DEFAULT_UPDATE_TIME)*8)/1024));
            local_status = streamStatus;
            //bitrate = 0;
            //sleepCounter = 0;
            //notDDosCounter = RESPONSES_PER_DEFAULT_UPDATE_TIME;
        } else {
            strRequestLink += "&bitrate=0";
        }
        strRequestLink += "&cc="+std::to_string(ccCounter)+"&udp="+std::to_string(lostUdpPackagesCounter);
        strRequestLink += "&raise="+std::to_string(udpRaiseCounter);
        if (justStart) {
            local_status = streamStatus;
            justStart = 0;
        }
        strRequestLink += "&status="+std::to_string(local_status);
        strRequestLink += "&fastStatus="+std::to_string(fastStatus);

        if (scrambledStatus != -1) {
            strRequestLink +="&scrambled="+std::to_string(scrambledStatus);
        } else {
            strRequestLink += "&scrambled=-1";
        }
        lostUdpPackagesCounter = 0;
        udpRaiseCounter = 0;
        ccCounter = 0;
        scrambledStatus = -1;
        //self DDos block
        if (--notDDosCounter > 0) {
            curl_easy_setopt(curl, CURLOPT_URL, strRequestLink.c_str());
            curl_easy_perform(curl);
            std::cerr << strRequestLink << std::endl;
        }
        curl_easy_cleanup(curl);

        // сбрасываем все счетчики битрейтов перед следующей итерацией
        fastBitrateOneSec = 0;
        bitrateOneSec = 0;

        // пора обнулять минутный статус
        if (sleepCounter >= DEFAULT_UPDATE_TIME*1000000) {
            bitrate = 0;
            sleepCounter = 0;
            notDDosCounter = RESPONSES_PER_DEFAULT_UPDATE_TIME;
        }
    }
}

int main(int argc, char *argv[])
{
    /*time_t seconds1, seconds2, secondsDelta;

    seconds1 = time(NULL);
    sleep(5);
    seconds2 = time(NULL);
    delta = seconds2 - seconds1;
    int iiiii = sizeof(time_t);
    int p = 0;*/


//    std::string line="<?xml version=\"1.0\"?><commands><getObjects name=\"\"/></commands>";
//    char * data = new char[line.size() + 1 + 4 + 4];
//    strcpy(data+4, line.c_str());
//    *data = 0;
//    *(data+1) = 0;
//    *(data+2) = 0;
//    *(data+3) = line.size();
//    *(data+line.size()+4+1)=0xff;
//    *(data+line.size()+4+2)=0xff;
//    *(data+line.size()+4+3)=0xff;
//    *(data+line.size()+4+4)=0xff;
//    *(data+line.size()+4+5)='\0';



    std::thread t(sendStatusThread, argv);
    //argv parsing
    for (int i = 1; i < argc-1; i++) {
        if (std::string(argv[i]) == "-a") {
            addressIndex = ++i;
        } else if (std::string(argv[i]) == "-p") {
            portIndex = ++i;
        } else if (std::string(argv[i]) == "-i") {
            idIndex = ++i;
        } else if (std::string(argv[i]) == "-n") {
            nameIndex = ++i;
        } else if (std::string(argv[i]) == "-r") {
            reportLinkIndex = ++i;
        } else if (std::string(argv[i]) == "-m") {
            minBitrateIndex = ++i;
        }
        else {
            help();
            return -1;
        }
    }

   int sock, status;//, socklen;
   socklen_t socklen;
   struct sockaddr_in saddr;
   struct ip_mreq imreq;

   // set content of struct saddr and imreq to zero
   memset(&saddr, 0, sizeof(struct sockaddr_in));
   memset(&imreq, 0, sizeof(struct ip_mreq));

   // open a UDP socket
   sock = socket(PF_INET, SOCK_DGRAM, IPPROTO_UDP); //was IPPROTO_IP
   if ( sock < 0 )
     perror("Error creating socket"), exit(0);

   int enable = 1;
   status = setsockopt(sock, SOL_SOCKET, SO_REUSEADDR, &enable, sizeof(int));



   saddr.sin_family = PF_INET;
   saddr.sin_port = htons(atoi(argv[portIndex])); // listen on port 4096
   //saddr.sin_addr.s_addr = htonl(INADDR_ANY); // bind socket to any interface
   saddr.sin_addr.s_addr = inet_addr(argv[addressIndex]);
   status = bind(sock, (struct sockaddr *)&saddr, sizeof(struct sockaddr_in));

   if ( status < 0 )
     perror("Error binding socket to interface"), exit(0);

   imreq.imr_multiaddr.s_addr = inet_addr(argv[addressIndex]);
   imreq.imr_interface.s_addr = INADDR_ANY; // use DEFAULT interface

   // JOIN multicast group on default interface
   status = setsockopt(sock, IPPROTO_IP, IP_ADD_MEMBERSHIP,
              (const void *)&imreq, sizeof(struct ip_mreq));

   //test
   struct timeval timeout;
   timeout.tv_sec = 0;
   timeout.tv_usec = 900000; //set agaib to 100

//   int time_out = 2000;
   status = setsockopt (sock, SOL_SOCKET, SO_RCVTIMEO, (char*)&timeout, sizeof (timeout));
   //\test

   socklen = sizeof(struct sockaddr_in);

   uint16_t eseq = 0;
   uint16_t seq = 0;
   std::cerr << currentDateTime() << " Capturing from: " << argv[addressIndex] << ":" << argv[portIndex] << " is started\n";



   for(;;){
       status = recvfrom(sock, buffer, MAXBUFSIZE, 0,
                         (struct sockaddr *)&saddr, &socklen);

       if (status > 0) {
           bitrate += status;
           bitrateOneSec += status;
           fastBitrateOneSec += status;
           if (streamStatus != 1) {
               streamStatus = 1;
               //updateStreamStatusInDB(argv, 0);
           }
//           if (DUMP) {
//               if (!needToWriteDumpAndExit) {
//                   copyToDumpBuffer();
//               } else {

//                   writeDumpAndClose();
//               }
//           }

           int header_size = 12 + 4 * (buffer[0] & 16);
           seq = (buffer[2] << 8)+buffer[3];

           if (!eseq && seq) {
               eseq = seq;
           } else {
               eseq++;
           }

           if (seq != eseq) {
               int packages_counter = (seq-eseq);
               if (packages_counter < 0) {
                   packages_counter = packages_counter + 65535;
               }
               lostUdpPackagesCounter += packages_counter;
               udpRaiseCounter++;
               //std::cerr << currentDateTime() << " SEQ = " << seq << " ESEC = " << eseq << "\n";
               eseq = seq;
           }

           if (!pcr_pid) {
               if (maxBuffCounter++ < PACKETS_TO_MAX_BUFFER) {
                   for (int i = header_size; i < status; i++) {
                       *big_buffer++ = buffer[i];
                       maxBuffSize++;
                   }
               } else {
                   uint16_t pmt_pid = getPidFromTable(start_big_buffer, maxBuffSize, 1, 0);
                   pcr_pid = getPidFromTable(start_big_buffer, maxBuffSize, 0, pmt_pid);
                   if (pcr_pid != 0) {
                       std::cout << "pid = " <<std::to_string(pcr_pid) << std::endl;
                       delete [] start_big_buffer;
                   } else {
                       std::cout << "pid = -1" << std::endl;
                       big_buffer = start_big_buffer;
                       maxBuffCounter = 0;
                   }
               }
           }
           else {
               //error_flag = 1;

               //checkCC(&buffer[header_size], &pcr_pid, status); //old
               checkCC(&buffer[header_size], &pcr_pid, status-header_size);
           }
           //std::cout << QString::number(seq).toStdString() << "      "<< QString::number(seq).toStdString() <<  "\n";
       }
       if (status == -1) {
           if (streamStatus != 0) {
               streamStatus = 0;
               //updateStreamStatusInDB(argv, 0);
           }
       }

//       //check need or not send errors report
//       if (udpRaiseCounter || lostUdpPackagesCounter || ccCounter) {
//           if ((time(NULL) - lastErrorTime) >= 1) {
//               lastErrorTime = time(NULL);
//               //send error
//               std::cerr << currentDateTime() << " lostUdpPackagesCounter = " << lostUdpPackagesCounter << " udpRaiseCounter = " << udpRaiseCounter << " ccCounter = " << ccCounter << "\n";
//               //выполняем инициализацю
//               curl = curl_easy_init();
//               if(curl) {
//                   //curlIsDiong = 1;
//                   //задаем опцию - получить страницу-lcurl по адресу http://google.com
//                   std::string strRequestLink = std::string(argv[reportLinkIndex])+"?multicast=";
//                   strRequestLink += std::string(argv[addressIndex])+"&cc="+std::to_string(ccCounter)+"&udp="+std::to_string(lostUdpPackagesCounter);
//                   strRequestLink +="&raise="+std::to_string(udpRaiseCounter)+"&id="+std::string(argv[idIndex])+"&name="+std::string(argv[nameIndex]);
//                   strRequestLink +="&status=-1&event=777";
////                   strRequestLink +="&noinput="+std::to_string(noInput);
////                   strRequestLink +="&error="+std::to_string(error_flag);
//                   std::cerr << curl_easy_setopt(curl, CURLOPT_URL, strRequestLink.c_str()) << std::endl;
//                   //вызываем функцию, выполняющюю все операции, заданные в опциях (получение страницы, передача данных и т.д.), результат - объект типа CURLcode
//                   std::cerr << curl_easy_perform(curl) << std::endl;
//                   //выполняем обязательное завершение сессии
//                   curl_easy_cleanup(curl);
//               }
//               lostUdpPackagesCounter = 0;
//               udpRaiseCounter = 0;
//               ccCounter = 0;
////               curlIsDiong = 0;
//              // error_flag = 0;
//           }
//       }
   }
   // shutdown socket
   shutdown(sock, 2);
   // close socket
   close(sock);
   return 0;
}

//void copyToDumpBuffer(){
//    uint temp[MAXBUFSIZE];
//    for (int i = 0; i < MAXBUFSIZE; i++) {
//        dump_buffer_old[i] = dump_buffer_current[i];
//        temp[i] = dump_buffer_current[i];
//    }
//    for (int i = 0; i < MAXBUFSIZE; i++) {
//        dump_buffer_current[i] = buffer[i];
//    }
//}

//void writeDumpAndClose(){
//    std::ofstream out("/tmp/dumpFastAnalyzer");
//    std::string hex_string;

//    out << std::to_string(errorByte);

//    create_hex_str(dump_buffer_old, 12, hex_string);
//    out << hex_string;
//    create_hex_str(dump_buffer_old+12, 188, hex_string);
////    out << hex_string;
////    create_hex_str(dump_buffer_old, 200, hex_string);
//    out << hex_string << "\n";
//    for (int i = 0; i < 6; i++) {
//        create_hex_str(dump_buffer_old+200+i*188, 188, hex_string);
//        out << hex_string << "\n";
//    }
//    out << "\n" << "\n";

//    create_hex_str(dump_buffer_current, 12, hex_string);
//    out << hex_string;
//    create_hex_str(dump_buffer_current+12, 188, hex_string);
////    out << hex_string;
////    create_hex_str(dump_buffer_current, 200, hex_string);
//    out << hex_string << "\n";
//    for (int i = 0; i < 6; i++) {
//        create_hex_str(dump_buffer_current+200+i*188, 188, hex_string);
//        out << hex_string << "\n";
//    }
//    out << "\n" << "\n";

//    create_hex_str(buffer, 12, hex_string);
//    out << hex_string;
//    create_hex_str(buffer+12, 188, hex_string);
////    out << hex_string;
////    create_hex_str(buffer, 200, hex_string);
//    out << hex_string << "\n";
//    for (int i = 0; i < 6; i++) {
//        create_hex_str(buffer+200+i*188, 188, hex_string);
//        out << hex_string << "\n";
//    }

//    /*create_hex_str(dump_buffer_current, MAXBUFSIZE, hex_string);
//    out << hex_string;

//    create_hex_str(buffer, MAXBUFSIZE, hex_string);
//    out << hex_string;*/

//    out.close();
//    exit(1);
//}

void updateStreamStatusInDB(char *argv[], int key) {

    curl = curl_easy_init();
    if(curl) {
        //curlIsDiong = 1;
        std::string strRequestLink = std::string(argv[reportLinkIndex])+"?multicast=";
        strRequestLink += std::string(argv[addressIndex]);
        strRequestLink += "&id="+std::string(argv[idIndex])+"&name="+std::string(argv[nameIndex]);
        strRequestLink += "&status="+std::to_string(streamStatus);
        if (key == 1) {
            strRequestLink += "&bitrate="+std::to_string((((bitrate/DEFAULT_UPDATE_TIME)*8)/1024));
            bitrate = 0;
            strRequestLink += "&secbitrate="+std::to_string(((bitrateOneSec*8)/1024));
            bitrateOneSec = 0;
        } else if (key == 2) {
            strRequestLink += "&secbitrate="+std::to_string(((bitrateOneSec*8)/1024));
            bitrateOneSec = 0;
        }
        strRequestLink += "&event="+std::to_string(key);
        std::cerr << curl_easy_setopt(curl, CURLOPT_URL, strRequestLink.c_str()) << std::endl;
        std::cerr << curl_easy_perform(curl) << std::endl;
        curl_easy_cleanup(curl);
    }
    //curlIsDiong = 0;
}

uint16_t getPidFromTable(uint8_t *p_big_buffer, uint buffer_size, bool is_pmt_pid, uint16_t table_pid) {
    uint32_t ts_header_dw = 0x47;
    uint16_t program_number = 0;
    uint16_t result_pid = 0;
    uint pmt_while_counter = 0;
    uint8_t byte_from_buff = 0;
    while (p_big_buffer - start_big_buffer < buffer_size) {
        if (*p_big_buffer++ == 0x47) {
            for (int i = 0; i < 3; i++) {
                byte_from_buff = *p_big_buffer++;
                ts_header_dw <<=8;
                ts_header_dw += byte_from_buff;
            }
            if (!(ts_header_dw & 0x800000) && ts_header_dw & 0x400000 && (ts_header_dw & 0x1fff00)>>8 == table_pid) {
                p_big_buffer += 9;
                if (is_pmt_pid) {
                    while (!program_number) {
                        program_number += *p_big_buffer++;
                        program_number <<=8;
                        program_number += *p_big_buffer++;
                        if (!program_number) {
                            pmt_while_counter++;
                        }
                        if (pmt_while_counter > 10) {
                            return 0;
                        }
                    }
                }
                result_pid = *p_big_buffer++;
                result_pid <<=8;
                result_pid += *p_big_buffer++;
                result_pid &= 0x1FFF;
                return result_pid;
            } else {
                ts_header_dw = 0x47;
            }
        }
    }
    return result_pid;
}

//void checkCC(uint8_t *buffer, uint16_t *pid, int size) {
//    try {
//        buffer -=5;
//        for (int j = 0; j < BYTES_TO_COPY; j++) {
//           *(buffer+j) = slidingArr[j];
//        }
//        int i = 0;
//        uint32_t header_dw = 0;
//        while (i < size) {
//           //error_flag = 1;
//           if (*(buffer+i) == 0x47) {
//               //error_flag = 1;
//               header_dw = *(buffer+i+1);
//               header_dw <<= 8;
//               header_dw += *(buffer+i+2);
//               header_dw <<= 8;
//               header_dw += *(buffer+i+3);
//               uint8_t discontinuity_indicator = 0;
//               //find discontinuity indicator
//               if (header_dw & 0x20 && *(buffer+i+4)) { //??? 0x20 10 – adaptation field only, no payload,11 – adaptation field followed by payload,
//                   discontinuity_indicator = (*(buffer+i+5)) & 0x80;
//               }
//               if (header_dw & 0x10 && (header_dw & 0x1fff00)>>8 == *pid && !discontinuity_indicator) {
//                   //error_flag = 0;
//                   if (cc == -1 || discontinuity_indicator) {
////                       cc = header_dw & 0xf;
////                       ecc = cc;
//                         ecc = header_dw & 0xf;
//                   }
//                   cc = header_dw & 0xf;
//                   if (ecc != cc) {
//                       if (!ccErrorOccurcs) {
//                           ccErrorOccurcs = 1;
//                       } else {
////                           errorByte = i-5;
//                           ccCounter++;
//                           ecc = cc+1;
//                           //std::cout << "Error!!!" << "\n";
//                           if (ecc > 15) {
//                               ecc = 0;
//                           }
////                           needToWriteDumpAndExit = 1;
//                       }
//                   } else {
//                       ccErrorOccurcs = 0;
//                       ecc++;
//                       if (ecc > 15) {
//                           ecc = 0;
//                       }
//                   }
//               }
//           }
//           i++;
//        }
//        for (int j = 0; j < BYTES_TO_COPY; j++) {
//           slidingArr[j] = *(buffer+i+j);
//        }
////        if (error_flag == 1) {
////            int p = 0;
////        }
//    }  catch(...) {
//        std::cerr << currentDateTime() << "Error ocurs" << "\n";
//    }
//}

void checkCC(uint8_t *buffer, uint16_t *pid, int size) {
    int tsPacketsCount = size/DEFAULT_TS_PACKET_SIZE;
    int tsPacketNumber = 0;
    int i = 0;
    uint32_t header_dw = 0;
    while (i+tsPacketNumber*DEFAULT_TS_PACKET_SIZE < size-5 && tsPacketNumber < tsPacketsCount) {
        if (*(buffer+i+tsPacketNumber*DEFAULT_TS_PACKET_SIZE) == 0x47) {
            header_dw = *(buffer+i+1+tsPacketNumber*DEFAULT_TS_PACKET_SIZE);
            header_dw <<= 8;
            header_dw += *(buffer+i+2+tsPacketNumber*DEFAULT_TS_PACKET_SIZE);
            header_dw <<= 8;
            header_dw += *(buffer+i+3+tsPacketNumber*DEFAULT_TS_PACKET_SIZE);




            uint8_t discontinuity_indicator = 0;
            //find discontinuity indicator
            if (header_dw & 0x20 && *(buffer+i+4+tsPacketNumber*DEFAULT_TS_PACKET_SIZE)) { //??? 0x20 10 – adaptation field only, no payload,11 – adaptation field followed by payload,
                discontinuity_indicator = (*(buffer+i+5+tsPacketNumber*DEFAULT_TS_PACKET_SIZE)) & 0x80;
            }
            if (header_dw & 0x10 && (header_dw & 0x1fff00)>>8 == *pid && !discontinuity_indicator) {
                if (cc == -1 || discontinuity_indicator) {
                    ecc = header_dw & 0xf;
                }

                //scrabling control
                scrambled = (header_dw & 0xC0) ? 1 : 0;

                //int tmp = scrambled;
                if (scrambled != lastScrambled) {
                    if (scrambledStatus == -1) {
                        lastScrambled = scrambled;
                        scrambledStatus = scrambled;
                        std::cerr << std::to_string(scrambledStatus) << std::endl;
                    }
                }

                cc = header_dw & 0xf;
                if (ecc != cc) {
                    if (!ccErrorOccurcs) {
                        ccErrorOccurcs = 1;
                    } else {
                        ccCounter++;
                        ecc = cc+1;
                        //std::cout << "Error!!!" << "\n";
                        if (ecc > 15) {
                            ecc = 0;
                        }
                    }
                } else {
                    ccErrorOccurcs = 0;
                    ecc++;
                    if (ecc > 15) {
                        ecc = 0;
                    }
                }
            }
            i = 0;
            tsPacketNumber++;
            continue;
        }
        i++;
    }
}

void help() {
    std::cout << "HELP! SOON" << "\n";
}
