#include <iostream>
#include <arpa/inet.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>

#define DEFAULT_TS_PACKET_SIZE 188
#define AMOUNT_TS_PACKETS_IN_RTP_PACKET 7
#define MIN_RTP_HEADER_SIZE 12
#define MAX_RTP_HEADER_SIZE 76 // 12+4*16
#define READ_N_BYTES_PER_ITERATION MAX_RTP_HEADER_SIZE + \
        AMOUNT_TS_PACKETS_IN_RTP_PACKET * DEFAULT_TS_PACKET_SIZE

void argv_parser(int *argc, char *argv[]);
void join_mcast(int *sock, socklen_t *socklen, struct sockaddr_in *saddr, char *argv[]);
void leave_mcast(int *sock);
// get PMT or PCR pid from TS package if it exist
uint16_t get_pid_from_table(uint8_t *p_ts_package, bool is_pmt_pid, uint16_t table_pid);
// find cc error in TS package if it exist
int check_ts_cc(uint8_t *p_ts_package, uint16_t *pid);
// get current datetime, format is YYYY-MM-DD HH:mm:ss
const std::string current_datetime();
// get current epoch time in ms
long int epoch_ms();
void help();
int addressIndex, portIndex, idIndex, nameIndex;


int main(int argc, char *argv[])
{
    // parse argv and set argv indexes
    argv_parser(&argc, argv);


    int sock;
    socklen_t socklen;
    struct sockaddr_in saddr;
    join_mcast(&sock, &socklen, &saddr, argv);
    std::cout << current_datetime() << " Capturing_from: " << argv[addressIndex] << ":" << argv[portIndex] << std::endl;

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
                //std::cerr << current_datetime() << " SEQ = " << seq << " ESEC = " << eseq << "\n";
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
                        pmt_pid = get_pid_from_table(&rtp_packages_buff[rtp_header_size + \
                                ts_package_index*DEFAULT_TS_PACKET_SIZE], 1, 0);
                    // try to find pcr_pid
                    } else
                    {
                        pcr_pid = get_pid_from_table(&rtp_packages_buff[rtp_header_size + \
                                ts_package_index*DEFAULT_TS_PACKET_SIZE], 0, pmt_pid);
                    }
                // try to find cc value
                } else
                {
                    cc_error_raise_counter += check_ts_cc(&rtp_packages_buff[rtp_header_size + \
                            ts_package_index*DEFAULT_TS_PACKET_SIZE], &pcr_pid);
                }
            }
        }
        // find difference between now and the last_report_time_ms
        last_report_time_difference_ms = epoch_ms() - last_report_time_ms;
        // need to send the report
        if (last_report_time_difference_ms > 1000)
        {
            bitrate_kbs = read_bytes_sum*8/last_report_time_difference_ms*1000/1024;
            std::cout << current_datetime() << " Bitrate: " << std::to_string(bitrate_kbs) << " Kbit/s";
            if (udp_error_raise_counter)
            {
                std::cout << " UDP_errors: " << std::to_string(udp_error_raise_counter);
            }
            if (udp_lost_packages_counter)
            {
                std::cout << " UDP_lost_packages: " << std::to_string(udp_lost_packages_counter);
            }
            if (cc_error_raise_counter)
            {
                std::cout << " CC_errors: " << std::to_string(cc_error_raise_counter);
            }
            std::cout << " PCR_pid: " << std::to_string(pcr_pid);
            std::cout << std::endl;
            // reset variables
            read_bytes_sum = 0;
            udp_error_raise_counter = 0;
            udp_lost_packages_counter = 0;
            cc_error_raise_counter = 0;
            last_report_time_ms = epoch_ms();
        }
    }
    leave_mcast(&sock);
    return 0;
}


uint16_t get_pid_from_table(uint8_t *p_ts_package, bool is_pmt_pid, uint16_t table_pid) {
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


void argv_parser(int *argc, char *argv[])
{
    for (int i = 1; i < *argc-1; i++)
    {
        if (std::string(argv[i]) == "-a")
        {
            addressIndex = ++i;
        }
        else if (std::string(argv[i]) == "-p")
        {
            portIndex = ++i;
        }
        else if (std::string(argv[i]) == "-i")
        {
            idIndex = ++i;
        }
        else if (std::string(argv[i]) == "-n")
        {
            nameIndex = ++i;
        }
        else
        {
            help();
            exit(1);
        }
    }
}


void join_mcast(int *sock, socklen_t *socklen, struct sockaddr_in *saddr, char *argv[])
{
    int status;
    struct ip_mreq imreq;
    // set content of struct saddr and imreq to zero
    memset(saddr, 0, sizeof(struct sockaddr_in));
    memset(&imreq, 0, sizeof(struct ip_mreq));
    // open the UDP socket
    *sock = socket(PF_INET, SOCK_DGRAM, IPPROTO_UDP);
    if (*sock < 0)
    {
        std::cerr << "Error creating socket" << std::endl;
        exit(1);
    }
    int enable = 1;
    status = setsockopt(*sock, SOL_SOCKET, SO_REUSEADDR, &enable, sizeof(int));
    saddr->sin_family = PF_INET;
    // listen port
    saddr->sin_port = htons(atoi(argv[portIndex]));
    saddr->sin_addr.s_addr = inet_addr(argv[addressIndex]);
    status = bind(*sock, (struct sockaddr *)saddr, sizeof(struct sockaddr_in));
    if (status < 0)
    {
        std::cerr << "Error binding socket to interface" << std::endl;
        exit(1);
    }
    imreq.imr_multiaddr.s_addr = inet_addr(argv[addressIndex]);
    // use DEFAULT interface
    imreq.imr_interface.s_addr = INADDR_ANY;
    // JOIN multicast group on the default interface
    status = setsockopt(*sock, IPPROTO_IP, IP_ADD_MEMBERSHIP, (const void *)&imreq, sizeof(struct ip_mreq));
    // set time to live for the socket
    struct timeval timeout;
    timeout.tv_sec = 0;
    timeout.tv_usec = 100000; // 0.1 sec
    status = setsockopt (*sock, SOL_SOCKET, SO_RCVTIMEO, (char*)&timeout, sizeof (timeout));
    *socklen = sizeof(struct sockaddr_in);
}


void leave_mcast(int *sock)
{
    // shutdown socket
    shutdown(*sock, 2);
    // close socket
    close(*sock);
}


void help() {
    std::cout << "HELP! SOON" << "\n";
}


const std::string current_datetime() {
    time_t     now = time(0);
    struct tm  tstruct;
    char       buf[80];
    tstruct = *localtime(&now);
    strftime(buf, sizeof(buf), "%Y-%m-%d %X", &tstruct);
    return buf;
}


long int epoch_ms()
{
    static struct timeval tp;
    gettimeofday(&tp, NULL);
    return tp.tv_sec * 1000 + tp.tv_usec / 1000;
}
