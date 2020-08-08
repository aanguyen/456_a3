# 456_a3

To run this program, call `./virtualrouter.sh <IP> <Port> <RouterID>` for every
router on the graph's topology, where <IP> and <Port> are the IP address and port
of where the NFE is running. <RouterID> should be different for each router that is ran.


Thanks to https://stackoverflow.com/questions/53074947/examples-for-search-graph-using-scipy
for the get_path function we use to find next hops for our routing table, as well
as the code for invoking scipy's Floyd-Warshall lowest path cost algorithm.