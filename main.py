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

def extract_domain_name(buf, position):
    domain_name = bytearray()
    # Used to detect compression loops
    original_position = position
    visited_positions = set()
    while True:
        if position in visited_positions:
            # We've detected a loop in compression pointers
            raise ValueError("Compression loop detected")
        if position >= len(buf):
            raise ValueError("Buffer overflow while parsing domain name")
        length = buf[position]
        # Check if this is a compression pointer (first two bits are set to 1)
        if (length & 0xC0) == 0xC0:
            if position + 1 >= len(buf):
                raise ValueError("Buffer overflow while parsing compression pointer")
            # Extract the offset (14 bits) from the two bytes
            offset = ((length & 0x3F) << 8) | buf[position + 1]
            # Only add compression pointer to visited positions if this isn't the first pointer
            if position != original_position:
                visited_positions.add(position)
            # Update position to the offset
            position = offset
            continue
        if length == 0:
            # End of domain name
            domain_name.append(0)
            position += 1
            break

        # Add this position to visited positions
        visited_positions.add(position)
        # Copy the length byte and the label content
        domain_name.append(length)
        position += 1
        if position + length > len(buf):
            raise ValueError("Buffer overflow while parsing label")
        domain_name.extend(buf[position : position + length])
        position += length
    return bytes(domain_name), position

def parse_questions(buf, qdcount):
    position = 12  # Skip the header
    questions = bytearray()
    domain_names = []
    for _ in range(qdcount):
        # Extract domain name with compression support
        domain_name, new_position = extract_domain_name(buf, position)
        domain_names.append(domain_name)
        # Extract type and class
        if new_position + 4 > len(buf):
            raise ValueError("Buffer overflow while parsing question type and class")
        type_bytes = buf[new_position : new_position + 2]
        class_bytes = buf[new_position + 2 : new_position + 4]
        # Add to the questions bytearray
        questions.extend(domain_name)
        questions.extend(type_bytes)
        questions.extend(class_bytes)

        # Update position for next question
        position = new_position + 4

    return bytes(questions), domain_names


def main():

    print("Logs from your program will appear here!")

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("127.0.0.1", 2053))

    while True:
        try:
            buf, source = udp_socket.recvfrom(512)
            print(f"Received {len(buf)} bytes from {source}")

            query_id, response_flags = parse_header(buf)

            qdcount = struct.unpack(">H", buf[4:6])[0]
            print(f"Question count: {qdcount}")

            header = query_id
            header += struct.pack(">H", response_flags)
            header += struct.pack(">H", qdcount)  # Number of questions
            header += struct.pack(">H", qdcount)  # Number of answers
            header += struct.pack(">H", 0)        # Number of authority records
            header += struct.pack(">H", 0)        # Number of additional records

            # Extract all question sections and domain names
            questions, domain_names = parse_questions(buf, qdcount)

            response = header + questions

            for domain_name in domain_names:
                answer = domain_name
                answer += struct.pack(">H", 1)  # Type: A
                answer += struct.pack(">H", 1)  # Class: IN
                answer += struct.pack(">I", 60)  # TTL: 60 seconds
                answer += struct.pack(">H", 4)  # Data length: 4 bytes (for IPv4)
                answer += socket.inet_aton("8.8.8.8")  # IP address: 8.8.8.8
                response += answer

            print(f"Sending response of {len(response)} bytes")
            udp_socket.sendto(response, source)
        except Exception as e:
            print(f"Error: {e}")
            break


if __name__ == "__main__":
    main()