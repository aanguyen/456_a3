#!/usr/bin/env python3
import sys
import struct
from socket import *
import heapq


def dijkstra(adjacency, target):
    dist = {vert: (float("inf"), None) for vert in adjacency}
    dist[target] = (0, 0)
    visited = set()
    q = [(0, target)]

    # cost, id
    while q:
        cur = heapq.heappop(q)
        cur_id = cur[1]
        visited.add(cur_id)

        sys.stdout.flush()
        for edge_data in adjacency[cur_id]:
            edge_cost = edge_data[2]
            dest = edge_data[0]
            if dist[cur_id][0] + edge_cost < dist[dest][0]:
                dist[dest] = (dist[cur_id][0] + edge_cost, dist[cur_id][1])

                if dest not in visited:
                    heapq.heappush(q, (dist[dest], dest))

                if cur_id == target:
                    dist[dest] = (dist[dest][0], dest)

    return dist


def create_lsa_msg(sender_id, sender_link_id, router_id, router_link_id, router_link_cost):
    return (struct.pack("!i", 3) +
            struct.pack("!i", int(sender_id)) +
            struct.pack("!i", int(sender_link_id)) +
            struct.pack("!i", int(router_id)) +
            struct.pack("!i", int(router_link_id)) +
            struct.pack("!i", int(router_link_cost))
            )


def read_lsa(data):
    sender_id = struct.unpack("!i", data[4:8])[0]
    sender_link_id = struct.unpack("!i", data[8:12])[0]
    router_id = struct.unpack("!i", data[12:16])[0]
    router_link_id = struct.unpack("!i", data[16:20])[0]
    router_link_cost = struct.unpack("!i", data[20:24])[0]
    return sender_id, sender_link_id, router_id, router_link_id, router_link_cost


def lsa_to_string(sender_id, sender_link_id, router_id, router_link_id, router_link_cost):
    return f" sender: {sender_id}, link: {sender_link_id}, router: {router_id}, router_link:{router_link_id}, link cost:{router_link_cost}"


def main(argv):
    if len(argv) != 4:
        print("Virtual router initialized incorrectly.")
        return
    nfe_ip = argv[1]
    nfe_port = int(argv[2])
    this_router_id = int(argv[3])

    # Internal router topology of the network
    # We will store this in the form:
    # this router id: [destination router id, link id connecting 2 routers, cost of this link]
    internal_topology = {this_router_id: []}
    print(f"INITIALIZED ROUTER {this_router_id}")
    # Send init message
    udp_socket = socket(AF_INET, SOCK_DGRAM)
    init_msg = struct.pack("!i", 1) + struct.pack("!i", this_router_id)
    udp_socket.sendto(init_msg, (nfe_ip, nfe_port))

    # Wait for init-reply
    resp, _ = udp_socket.recvfrom(4096)

    # Keep a set of known LSA messages from this router to know what to drop
    known_lsas = set()
    # Keep a set of unfulfilled links
    unfulfilled = {}
    # Send out edges in init-reply to immediate neighbours
    num_links = struct.unpack("!i", resp[4:8])
    start_bytes = 8
    direct_link_ids = []
    for _ in num_links:
        link_id = struct.unpack("!i", resp[start_bytes:start_bytes+4])[0]
        start_bytes += 4
        link_cost = struct.unpack("!i", resp[start_bytes:start_bytes+4])[0]
        start_bytes += 4
        lsa_msg = create_lsa_msg(this_router_id, link_id, this_router_id, link_id, link_cost)
        udp_socket.sendto(lsa_msg, (nfe_ip, nfe_port))
        known_lsas.add((this_router_id, link_id, link_cost))
        unfulfilled[link_id] = (this_router_id, link_cost)
        direct_link_ids.append(link_id)

    topology_update = False
    routing_table = []
    # Always be listening to incoming LSAs
    while True:
        resp, _ = udp_socket.recvfrom(4096)
        sender_id, sender_link_id, router_id, router_link_id, router_link_cost = read_lsa(resp)
        print(f"Received:{lsa_to_string(sender_id, sender_link_id, router_id, router_link_id, router_link_cost)}")

        if (router_id, router_link_id, router_link_cost) in known_lsas:
            # Drop it if we've already seen it
            print(f"Dropping:{lsa_to_string(sender_id, sender_link_id, router_id, router_link_id, router_link_cost)}")
        else:
            # Send the LSA from this router across all direct links to this router
            for link in direct_link_ids:
                lsa_msg = create_lsa_msg(this_router_id, link, router_id, router_link_id, router_link_cost)
                udp_socket.sendto(lsa_msg, (nfe_ip, nfe_port))
                print(f"Sending:{lsa_to_string(this_router_id, link, router_id, router_link_id, router_link_cost)}")
            # Add this LSA to our internal topology
            if router_link_id in unfulfilled:
                # If unfulfilled, then we update topology to include a new node
                topology_update = True
                # So we don't get null errors later
                if router_id not in internal_topology:
                    internal_topology[router_id] = []
                unfulfilled_link = unfulfilled.pop(router_link_id)
                if unfulfilled_link[0] not in internal_topology:
                    internal_topology[unfulfilled_link[0]] = []
                # cost = unfulfilled_link[1]
                # Add the link to EACH of the two sides it is connecting to
                internal_topology[router_id].append([unfulfilled_link[0], router_link_id, router_link_cost])
                internal_topology[unfulfilled_link[0]].append([router_id, router_link_id, router_link_cost])
            else:
                unfulfilled[router_link_id] = (router_id, router_link_cost)

            # Update our shortest distances using Dijkstras
            new_routing_table = dijkstra(internal_topology, this_router_id)

            # Log internal topology, if necessary
            if topology_update:
                with open(f"topology_{this_router_id}.out", "a") as f:
                    print("TOPOLOGY", file=f)
                    for router in internal_topology:
                        for connect in internal_topology[router]:
                            print(f"router:{router},router{connect[0]},linkid:{connect[1]},cost:{connect[2]}", file=f)
            topology_update = False

            # Log routing table (shortest distances), if necessary
            if new_routing_table != routing_table:
                with open(f"routingtable_{this_router_id}.out", "a") as f:
                    print("ROUTING", file=f)
                    for node in new_routing_table:
                        print(f"{node}:{new_routing_table[node][0]},{new_routing_table[node][1]}")
                routing_table = new_routing_table

            # Once we finish processing it add this to the known LSAs list
            known_lsas.add((router_id, router_link_id, router_link_cost))


if __name__ == '__main__':
    # params:
    # - IP address where NFE is listening
    # - port where NFE is listening
    # - router ID assigned to that instance of the virtual router
    main(sys.argv)
