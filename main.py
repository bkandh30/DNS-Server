import socket
import struct

def build_dns_response():
    transaction_id = struct.pack(">H", 1234)  # ID: 1234 (0x04d2)
    flags = struct.pack(">H", 0x8000)         # Flags: Standard response, no error
    qdcount = struct.pack(">H", 1)            # Number of questions
    ancount = struct.pack(">H", 1)            # Number of answers
    nscount = struct.pack(">H", 0)            # Number of authority records
    arcount = struct.pack(">H", 0)            # Number of additional records

    header = transaction_id + flags + qdcount + ancount + nscount + arcount

    question = b"\x0c" + b"codecrafters" + b"\x02" + b"io" + b"\x00"
    question += struct.pack(">H", 1)  # Type: A
    question += struct.pack(">H", 1)  # Class: IN


    adomain = b"\x0c" + b"codecrafters" + b"\x02" + b"io" + b"\x00"
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

            response = build_dns_response()

            udp_socket.sendto(response, source)
        except Exception as e:
            print(f"Error receiving data: {e}")
            break


if __name__ == "__main__":
    main()
