import socket
import struct
import argparse

def build_default_response(query_packet: bytes, qdcount:int, error=False):
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

    # Construct the header
    header = query_id
    header += struct.pack(">H", response_flags)
    header += struct.pack(">H", qdcount)  # Number of questions
    header += struct.pack(">H", qdcount)  # Number of answers
    header += struct.pack(">H", 0)        # Number of authority records
    header += struct.pack(">H", 0)        # Number of additional records

    # Extract all question sections and domain names
    questions, domain_names = parse_questions(query_packet, qdcount)

    response = header + questions

    for domain_name in domain_names:
        answer = domain_name
        answer += struct.pack(">H", 1)  # Type: A
        answer += struct.pack(">H", 1)  # Class: IN
        answer += struct.pack(">I", 60)  # TTL: 60 seconds
        answer += struct.pack(">H", 4)  # Data length: 4 bytes (for IPv4)
        answer += socket.inet_aton("8.8.8.8")  # IP address: 8.8.8.8
        response += answer
    return response

def extract_domain_name(query_packet:bytes, position:int):
    # Extract a domain name from the packet, handling compression
    domain_name = bytearray()
    original_position = position
    visited_positions = set()

    while True:
        if position in visited_positions:
            raise ValueError("Compression loop detected")
        if position >= len(query_packet):
            raise ValueError("Buffer overflow while parsing domain name")
        length = query_packet[position]

        # Check for compression pointer
        if (length & 0xC0) == 0xC0:
            if position + 1 >= len(query_packet):
                raise ValueError("Buffer overflow while parsing compression pointer")
            # Extract the offset (14 bits) from the two bytes
            offset = ((length & 0x3F) << 8) | query_packet[position + 1]
            # Only add compression pointer to visited positions if this isn't the first pointer
            if position != original_position:
                visited_positions.add(position)
            position = offset
            continue
        if length == 0:
            domain_name.append(0)
            position += 1
            break

        # Add this position to visited positions
        visited_positions.add(position)

        domain_name.append(length)
        position += 1
        if position + length > len(query_packet):
            raise ValueError("Buffer overflow while parsing label")
        domain_name.extend(query_packet[position : position + length])
        position += length
    return bytes(domain_name), position

def parse_questions(query_packet: bytes, qdcount:int):
    #Parse all the questions in the query 
    #Skip the header
    position = 12  
    questions = bytearray()
    domain_names = []
    for _ in range(qdcount):
        domain_name, new_position = extract_domain_name(query_packet, position)
        domain_names.append(domain_name)
        if new_position + 4 > len(query_packet):
            raise ValueError("Buffer overflow while parsing question type and class")
        type_bytes = query_packet[new_position : new_position + 2]
        class_bytes = query_packet[new_position + 2 : new_position + 4]
        # Add to the questions bytearray
        questions.extend(domain_name)
        questions.extend(type_bytes)
        questions.extend(class_bytes)

        # Update position for next question
        position = new_position + 4

    return bytes(questions), domain_names

def forward_query(query_packet:bytes, resolver_address, qdcount:int):
    query_id = query_packet[0:2]

    if qdcount > 1:
        questions, domain_names = parse_questions(query_packet, qdcount)

        all_answers = bytearray()

        for i in range(qdcount):
            single_query = create_single_question_query(query_packet, i)
            resolver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            resolver_socket.settimeout(5)
            resolver_socket.sendto(single_query, resolver_address)
            try:
                response, _ = resolver_socket.recvfrom(512)
                answer = parse_answer_section(response)
                all_answers.extend(answer)
            except socket.timeout:
                print(
                    f"Timeout while waiting for response from resolver for question {i+1}"
                )
            finally:
                resolver_socket.close()

        # Create our final response with all answers
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

        # Construct the header
        header = query_id
        header += struct.pack(">H", response_flags)
        header += struct.pack(">H", qdcount)  # Number of questions
        header += struct.pack(">H", qdcount)  # Number of answers
        header += struct.pack(">H", 0)        # Number of authority records
        header += struct.pack(">H", 0)        # Number of additional records

        response = header + questions + bytes(all_answers)
    else:
        resolver_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        resolver_socket.settimeout(5)
        resolver_socket.sendto(query_packet, resolver_address)
        try:
            response, _ = resolver_socket.recvfrom(512)
            response = query_id + response[2:]
        except socket.timeout:
            print("Timeout while waiting for response from resolver")
            response = build_default_response(query_packet, qdcount, error=True)
        finally:
            resolver_socket.close()
    return response

def create_single_question_query(original_query, question_index):
    # Copy the header from the original query
    new_query = bytearray(original_query[:12])
    # Set QDCOUNT to 1
    new_query[4:6] = struct.pack(">H", 1)

    # Extract the questions
    questions, _ = parse_questions(
        original_query, struct.unpack(">H", original_query[4:6])[0]
    )
    questions_list = split_questions(questions)
    new_query.extend(questions_list[question_index])
    return bytes(new_query)

def split_questions(questions_bytes):
    # Split multiple questions from a single query
    result = []
    position = 0
    while position < len(questions_bytes):
        start_position = position
        while position < len(questions_bytes):
            length = questions_bytes[position]
            if length == 0:
                position += 1
                break
            position += length + 1
        # Add Type and Class (4 bytes)
        position += 4
        # Store this question
        result.append(questions_bytes[start_position:position])
    return result


def parse_answer_section(response:bytes):
    # Skip over the header, questions and just return the answer section
    position = 12
    qdcount = struct.unpack(">H", response[4:6])[0]

    for _ in range(qdcount):
        while True:
            length = response[position]
            # Check for compression pointer
            if (length & 0xC0) == 0xC0:
                position += 2
                break
            if length == 0:
                position += 1
                break
            position += length + 1
        # Skip Type and Class (4 bytes)
        position += 4
    # The answer section starts here and continues to the end of the packet
    return response[position:]

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="DNS Server")
    parser.add_argument("--resolver", help="DNS resolver to forward queries to")
    args = parser.parse_args()
    # Extract resolver IP and port if provided
    resolver_address = None

    if args.resolver:
        resolver_ip, resolver_port = args.resolver.split(":")
        resolver_address = (resolver_ip, int(resolver_port))
        print(f"Using resolver: {resolver_address}")

    print("Logs from your program will appear here!")

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_socket.bind(("127.0.0.1", 2053))
    while True:
        try:
            buf, source = udp_socket.recvfrom(512)
            print(f"Received {len(buf)} bytes from {source}")
            # Parse the DNS header from the incoming packet
            query_id = buf[0:2]
            # Extract QDCOUNT - number of questions
            qdcount = struct.unpack(">H", buf[4:6])[0]
            print(f"Question count: {qdcount}")
            
            if resolver_address:
                response = forward_query(buf, resolver_address, qdcount)
            else:
                response = build_default_response(buf, qdcount)
            
            print(f"Sending response of {len(response)} bytes")
            udp_socket.sendto(response, source)
        except Exception as e:
            print(f"Error: {e}")
            break

if __name__ == "__main__":
    main()