import socket
import struct

domain_name = b"\x0c" + b"codecrafters" + b"\x02" + b"io" + b"\x00"

def build_dns_response(query_packet: bytes) -> bytes:
    #Parse the DNS header
    query_id = query_packet[0:2]
    flags = struct.unpack(">H", query_packet[2:4])[0]
    opcode = (flags >> 11) & 0xF
    rd = (flags >> 8) & 0x1

    #Response Flags
    response_flags = 0x8000
    response_flags |= opcode << 11
    response_flags |= rd << 8

    rcode = 0 if opcode == 0 else 4
    response_flags |= rcode

    transaction_id = query_id
    header_flags = struct.pack(">H", response_flags)
    qdcount = struct.pack(">H", 1)            # Number of questions
    ancount = struct.pack(">H", 1)            # Number of answers
    nscount = struct.pack(">H", 0)            # Number of authority records
    arcount = struct.pack(">H", 0)            # Number of additional records

    header = transaction_id + header_flags + qdcount + ancount + nscount + arcount

    question = domain_name
    question += struct.pack(">H", 1)  # Type: A
    question += struct.pack(">H", 1)  # Class: IN


    adomain = domain_name
    atype = struct.pack(">H", 1)        # Type: A
    aclass = struct.pack(">H", 1)       # Class: IN
    ttl = struct.pack(">I", 60)         # TTL: 60 seconds
    data_length = struct.pack(">H", 4)  # Data length: 4 bytes (for IPv4)
    ip = socket.inet_aton("8.8.8.8")    # IP address: 8.8.8.8

    answer = adomain + atype + aclass + ttl + data_length + ip

    return header + question + answer

def main():
    print("Logs from your program will appear here!")
    
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("127.0.0.1", 2053))
    
    while True:
        try:
            buf, source = udp_socket.recvfrom(512)

            response = build_dns_response(buf)

            udp_socket.sendto(response, source)
        except Exception as e:
            print(f"Error receiving data: {e}")
            break


if __name__ == "__main__":
    main()
