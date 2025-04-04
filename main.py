import socket
import struct

def parse_header(query_packet: bytes):
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

    return query_id, response_flags

def parse_question(query_packet: bytes):
    #Extract the Question section
    #Skip 12 bytes
    position = 12

    domain_name = bytearray()

    #Extract Domain Name
    while True:
        length = query_packet[position]
        if length == 0:
            domain_name.append(0)
            position += 1
            break
    
        domain_name.append(length)
        position += 1
        domain_name.extend(query_packet[position:position+length])
        position += length
    
    #Extract type and class
    type_bytes = query_packet[position:position+2]
    position += 2
    class_bytes = query_packet[position:position+2]
    position += 2
    
    question = bytes(domain_name) + type_bytes + class_bytes

    domain_name = bytes(domain_name)

    return question, domain_name

def build_dns_response(query_packet: bytes) -> bytes:
    query_id, response_flags = parse_header(query_packet)
    
    transaction_id = query_id
    header_flags = struct.pack(">H", response_flags)
    qdcount = struct.pack(">H", 1)            # Number of questions
    ancount = struct.pack(">H", 1)            # Number of answers
    nscount = struct.pack(">H", 0)            # Number of authority records
    arcount = struct.pack(">H", 0)            # Number of additional records

    header = transaction_id + header_flags + qdcount + ancount + nscount + arcount

    question, domain_name = parse_question(query_packet)

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
