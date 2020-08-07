#!/usr/bin/env python3
import sys
import struct
from socket import *


def dijkstra(adj, src_node):
    min_paths = {}
    # Set distances to all destinations to be infinity initially
    for dest in adj:
        min_paths[dest] = float("inf")
    # Set distance to source node to be 0


def main(argv):
    if len(argv) != 4:
        print("Virtual router initialized incorrectly.")
        return
    nfe_ip = argv[1]
    nfe_port = int(argv[2])
    router_id = int(argv[3])

    # Send init message
    udp_socket = socket(AF_INET, SOCK_DGRAM)
    init_msg = struct.pack("!i", 1) + struct.pack("!i", router_id)
    udp_socket.sendto(init_msg, (nfe_ip, nfe_port))

    # Wait for init-reply
    resp, _ = udp_socket.recvfrom(4096)
    print(resp)
    return


if __name__ == '__main__':
    # params:
    # - IP address where NFE is listening
    # - port where NFE is listening
    # - router ID assigned to that instance of the virtual router
    main(sys.argv)
