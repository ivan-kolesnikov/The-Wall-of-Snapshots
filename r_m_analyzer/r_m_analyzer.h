#ifndef R_M_ANALYZER_H
#define R_M_ANALYZER_H

#include <iostream>
#include <arpa/inet.h>
#include <string.h>
#include <sys/time.h>
#include <unistd.h>
#include "r_m_analyzer.h"
#include <netdb.h>

#define DEFAULT_TS_PACKAGE_SIZE 188
#define AMOUNT_TS_PACKAGES_IN_RTP_PACKAGE 7
#define MIN_RTP_HEADER_SIZE 12
#define MAX_RTP_HEADER_SIZE 76 // 12+4*16
#define READ_N_BYTES_PER_ITERATION MAX_RTP_HEADER_SIZE + \
        AMOUNT_TS_PACKAGES_IN_RTP_PACKAGE * DEFAULT_TS_PACKAGE_SIZE
#define MAX_LOST_PCR_PID_CONTINUOUSLY_VALUE 2000

int address_index = -1, port_index = -1, id_index = -1, name_index = -1, out_address_index = -1, out_port_index = -1;
int lost_pcr_pid_continuously_counter = 0;

void argv_parser(int *argc, char *argv[]);
void join_mcast(int *sock, socklen_t *socklen, struct sockaddr_in *saddr, char *argv[]);
void leave_mcast(int *sock);
int create_udp_socket(const char *hostname, int family, const char *service, sockaddr_storage *p_addr);
void destroy_udp_socket(int *udp_sock_fd);
// get PMT or PCR pid from TS package if it exist
uint16_t get_pid_from_table(uint8_t *p_ts_package, bool is_pmt_pid, uint16_t table_pid);
// find cc error in RTP package is it exist
int check_rtp_cc(uint8_t *p_rtp_package);
// find cc error in TS package if it exist
int check_ts_cc(uint8_t *p_ts_package, uint16_t *pid);
// get current datetime, format is YYYY-MM-DD HH:mm:ss
const std::string current_datetime();
// get current epoch time in ms
long int epoch_ms();
void help();

#endif // R_M_ANALYZER_H
