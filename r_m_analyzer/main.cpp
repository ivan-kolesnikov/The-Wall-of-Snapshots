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


#define DEFAULT_TS_PACKET_SIZE 188
#define AMOUNT_TS_PACKETS_IN_RTP_PACKET 7
#define MIN_RTP_HEADER_SIZE 12
#define MAX_RTP_HEADER_SIZE 76 // 12+4*16
#define READ_N_BYTES_PER_ITERATION MAX_RTP_HEADER_SIZE+AMOUNT_TS_PACKETS_IN_RTP_PACKET*DEFAULT_TS_PACKET_SIZE

int check_ts_cc(uint8_t *p_ts_package, uint16_t *pid);
long int epoch_ms();



void help();
//void sendStatusThread(char *argv[]);
uint16_t getPidFromTable(uint8_t *p_ts_package, bool is_pmt_pid, uint16_t table_pid);




//bool ccErrorOccurcs = 0;
time_t lastErrorTime = time(NULL);
//uint8_t slidingArr[BYTES_TO_COPY] = {0};
int addressIndex, portIndex, idIndex, nameIndex, reportLinkIndex, minBitrateIndex;
CURL *curl;

//uint8_t buffer[MAXBUFSIZE];
int needToUpdateStatus = 0;
//int errorByte = 0;



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

long int epoch_ms()
{
    static struct timeval tp;
    gettimeofday(&tp, NULL);
    return tp.tv_sec * 1000 + tp.tv_usec / 1000;
}


int main(int argc, char *argv[])
{
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

    int sock, status;
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
    // listen port
    saddr.sin_port = htons(atoi(argv[portIndex]));
    saddr.sin_addr.s_addr = inet_addr(argv[addressIndex]);
    status = bind(sock, (struct sockaddr *)&saddr, sizeof(struct sockaddr_in));
    if ( status < 0 )
      perror("Error binding socket to interface"), exit(0);
    imreq.imr_multiaddr.s_addr = inet_addr(argv[addressIndex]);
    imreq.imr_interface.s_addr = INADDR_ANY; // use DEFAULT interface
    // JOIN multicast group on default interface
    status = setsockopt(sock, IPPROTO_IP, IP_ADD_MEMBERSHIP,
               (const void *)&imreq, sizeof(struct ip_mreq));
    // set time to live for the socket
    struct timeval timeout;
    timeout.tv_sec = 0;
    timeout.tv_usec = 900000; // 0.9 sec
    status = setsockopt (sock, SOL_SOCKET, SO_RCVTIMEO, (char*)&timeout, sizeof (timeout));
    socklen = sizeof(struct sockaddr_in);
    // log
    std::cerr << currentDateTime() << " Capturing from: " << argv[addressIndex] << ":" << argv[portIndex] << " is started\n";



    int read_bytes = 0;
    int read_bytes_sum = 0;
    int rtp_header_size = 0;
    uint8_t rtp_packages_buff[READ_N_BYTES_PER_ITERATION];
    // continuety counter for rtp packages
    uint16_t eseq = 0;
    uint16_t seq = 0;
    int udp_error_raise_counter = 0;
    uint udp_lost_packages_counter = 0;
    uint16_t pcr_pid = 0;
    uint16_t pmt_pid = 0;
    int cc_error_raise_counter = 0;
    long int last_report_time_ms = epoch_ms();
    long int last_report_time_difference_ms = 0;
    int bitrate_kbs = 0;

    while (true)
    {
        // read data from the socket
        read_bytes = recvfrom(sock, rtp_packages_buff, READ_N_BYTES_PER_ITERATION, 0, (struct sockaddr *)&saddr, &socklen);
        if (read_bytes > 0)
        {
            // sum of bytes for the bitrate calculation
            read_bytes_sum += read_bytes;
            rtp_header_size = 12 + 4 * (rtp_packages_buff[0] & 16);

            // found rtp counter and check the order
            seq = (rtp_packages_buff[2] << 8)+rtp_packages_buff[3];
            if (!eseq && seq)
            {
                eseq = seq;
            } else
            {
                eseq++;
            }

            if (seq != eseq)
            {
                int delta_seq_eseq = (seq-eseq);
                if (delta_seq_eseq < 0)
                {
                    delta_seq_eseq = delta_seq_eseq + 65535;
                }
                udp_lost_packages_counter += delta_seq_eseq;
                udp_error_raise_counter++;
                //std::cerr << currentDateTime() << " SEQ = " << seq << " ESEC = " << eseq << "\n";
                eseq = seq;
            }
            // for each ts package
            for (int ts_package_index = 0; ts_package_index < AMOUNT_TS_PACKETS_IN_RTP_PACKET; ts_package_index++)
            {
                // if pcr_pid doesn't exist
                if (!pcr_pid)
                {
                    // if pmt_pid doesn't exist
                    if (!pmt_pid)
                    {
                        pmt_pid = getPidFromTable(&rtp_packages_buff[rtp_header_size+ts_package_index*DEFAULT_TS_PACKET_SIZE], 1, 0);
                    // try to find pcr_pid
                    } else
                    {
                        pcr_pid = getPidFromTable(&rtp_packages_buff[rtp_header_size+ts_package_index*DEFAULT_TS_PACKET_SIZE], 0, pmt_pid);
                    }
                // try to find cc value
                } else
                {
                    cc_error_raise_counter += check_ts_cc(&rtp_packages_buff[rtp_header_size+ts_package_index*DEFAULT_TS_PACKET_SIZE], &pcr_pid);
                }
            }
        }
        // find difference between now and the last_report_time_ms
        last_report_time_difference_ms = epoch_ms() - last_report_time_ms;
        // need to send the report
        if (last_report_time_difference_ms > 1000)
        {
            bitrate_kbs = read_bytes_sum*8/last_report_time_difference_ms*1000/1024;
            std::cout << std::to_string(bitrate_kbs) << " " << std::to_string(cc_error_raise_counter) << " " << std::to_string(udp_error_raise_counter)<<std::endl;
            read_bytes_sum = 0;
            last_report_time_ms = epoch_ms();
        }
    }
    // shutdown socket
    shutdown(sock, 2);
    // close socket
    close(sock);
    return 0;
}

/*
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
*/


uint16_t getPidFromTable(uint8_t *p_ts_package, bool is_pmt_pid, uint16_t table_pid) {
    uint32_t ts_header_dw = 0x47;
    uint16_t program_number = 0;
    uint16_t result_pid = 0;
    uint pmt_while_counter = 0;
    uint8_t byte_from_buff = 0;
    if (*p_ts_package++ == 0x47)
    {
        for (int i = 0; i < 3; i++)
        {
            byte_from_buff = *p_ts_package++;
            ts_header_dw <<=8;
            ts_header_dw += byte_from_buff;
        }
        if (!(ts_header_dw & 0x800000) && ts_header_dw & 0x400000 && (ts_header_dw & 0x1fff00)>>8 == table_pid)
        {
            p_ts_package += 9;
            if (is_pmt_pid)
            {
                while (!program_number)
                {
                    program_number += *p_ts_package++;
                    program_number <<=8;
                    program_number += *p_ts_package++;
                    if (!program_number)
                    {
                        pmt_while_counter++;
                    }
                    if (pmt_while_counter > 10)
                    {
                        return 0;
                    }
                }
            }
            result_pid = *p_ts_package++;
            result_pid <<=8;
            result_pid += *p_ts_package++;
            result_pid &= 0x1FFF;
            return result_pid;
        } else
        {
            return 0;
        }
    }
    return result_pid;
}

int check_ts_cc(uint8_t *p_ts_package, uint16_t *pid) {
    uint32_t header_dw = 0;
    static int8_t cc = -1;
    static int8_t ecc = -1;
    static bool cc_error_occurs = 0;
    int has_cc_error = 0;

    if (*p_ts_package == 0x47)
    {
        header_dw = *(p_ts_package+1);
        header_dw <<= 8;
        header_dw = *(p_ts_package+2);
        header_dw <<= 8;
        header_dw = *(p_ts_package+3);
        uint8_t discontinuity_indicator = 0;
        // if discontinuity indicator exists
        if (header_dw & 0x20 && *(p_ts_package+4)) {
            // 0x20 10 – adaptation field only, no payload,11 – adaptation field followed by payload,
            discontinuity_indicator = (*(p_ts_package+4)) & 0x80;
        }
        if (header_dw & 0x10 && (header_dw & 0x1fff00)>>8 == *pid && !discontinuity_indicator) {
            if (cc == -1 || discontinuity_indicator)
            {
                ecc = header_dw & 0xf;
            }
            cc = header_dw & 0xf;
            if (ecc != cc)
            {
                if (!cc_error_occurs)
                {
                    cc_error_occurs = 1;
                } else
                {
                    has_cc_error = 1;
                    ecc = cc+1;
                    //std::cout << "Error!!!" << "\n";
                    if (ecc > 15)
                    {
                        ecc = 0;
                    }
                }
            } else
            {
                cc_error_occurs = 0;
                ecc++;
                if (ecc > 15)
                {
                    ecc = 0;
                }
            }
        }
    }
    return has_cc_error;
}

void help() {
    std::cout << "HELP! SOON" << "\n";
}
