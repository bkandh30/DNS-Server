# DNS Server Implementation

The DNS server works on `PORT: 53` and **UDP Protocol**.

To query the DNS servers on your own terminal, you can use `dig` or Domain Information Groper command. It provides detailed information about domain names, IP addresses, and DNS records.

```bash
dig google.com
```

If it is giving a timeout error, it means your network's default server is broken or slow. Try this instead:

```bash
dig google.com @8.8.8.8
```

It will give you an output like this:

```bash
; <<>> DiG 9.10.6 <<>> google.com @8.8.8.8
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 6484
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 512
;; QUESTION SECTION:
;google.com.			IN	A

;; ANSWER SECTION:
google.com.		147	IN	A	142.250.72.142

;; Query time: 44 msec
;; SERVER: 8.8.8.8#53(8.8.8.8)
;; WHEN: Thu Apr 03 21:36:57 MST 2025
;; MSG SIZE  rcvd: 55
```

## Protocols

DNS is built on **UDP or User Datagram Protocol**. This is because:

- UDP is **connectionless** - it sends packets without setting up a handshake and has a lower overhead than TCP.
- It is perfect for sending small amounts of data quickly without needing the complexity of TCP.
- It scales well for huge number of DNS queries happening around the world every second.
- Since each DNS request is independent, using a stateless protocol like UDP makes servers simpler and faster as they don't have to keep a track of millions of active connections.

However, **if the DNS response is too big, it can exceed 512 bytes**. DNS then falls back to TCP to handle the larger response. Also, for certain types of queries (like zone transfers between DNS servers), TCP is mandatory.

## Message

All communications in DNS protocol are carried in a single format called a "message". Each message consists of 5 sections: header, question, answer, authority, and an additional space.

Domain names in DNS packets are encoded as a sequence of labels.

Labels are encoded as `<length><content>`, where `<length>` is a single byte that specifies the length of the label, and `<content>` is the actual content of the label. The sequence of labels is terminated by a null byte (`\x00`).

## Header Section Structure

A header field (flags) controls the content of the other 4 sections.

The header section consists of the following fields: _Identification, Flags, Number of questions, Number of answers, Number of authority resource records (RRs), and Number of additional RRs_. Each field is 16 bits long, and appears in the order given. The identification field is used to match responses with queries. After the flags word, the header ends with four 16-bit integers which contain the number of records in each of the sections that follow, in the same order.

## Question Section Structure

The question section contains a list of questions (usually 1) that the sender wants to ask the receiver. This section is present in both query and reply packets.

Each question has the following structure:

- Name: A domain name, represented as a sequence of labels.
- Type: The type of record.
- Class; Usually set to 1.

## Answer Section Structure

Answer section contains a list of resource records, which are answers to the questions asked in the question section.

Each RR has: Name, Type, Class, TTL (Time to Live), Length and Data. TTL is the duration in seconds a record can be cached before querying.

## Parsing the Header Section

From the actual data which is received as a bytes object, the header section is parsed.

The first two bytes of the packet contains the query identifier.

OPCODE is retrieved from the next two bytes by unpacking them as 16-bit signed integer and shifting them by 11 bits to the right and masking with `0xF` to generate the 4-bit opcode to the least significant position.

RD Flag is retrieved from the same two bytes that were used for OPCODE where they are unpacked as 16-bit signed integer and shifting them by 8 bits to the right and masking with `0x1` to generate its value (either 0 or 1).

As a result, we are able to parse the query ID, OPCODE, and RD flag.

Based on these parameter, we're also going to generate the response flags.

The response flags start with the default value of `0x8000` which sets the QR bit to 1, indicating that this packet is a response. The OPCODE is shifted by 11 bits to left and added to the response flag so that both the response and query carries the same OPCODE. The RD flag is shifted by 8 bits to the left and added to the response flags. If the OPCODE indicates a standard query then it sets RCODE to 0 otherwise, it sets RCODE to 4 which indicates **NOT IMPLEMENTED**. The RCODE is then incorporate into the response flags by setting the lowest 4 bits.

## Parsing Question Section

The first 12 bytes that are used for header section are skipped.

The domain name is stored in a special format where each label is preceded by a length byte. If the length is 0, it means the domain name is finished. The 0 byte is added to the end, position is incremented and the loop breaks. Otherwise, it appends the length byte to the `domain_name`, then reads the next `length` bytes. This process continues until the entire domain name is extracted.

After the domain name, the function reads the next 2 bytes as the question type and it then reads the following 2 bytes as the question class.

The question section is then constructed by concatenating the extracted domain name, the type bytes, and the class bytes. The domain name is also separately converted to a bytes object.

## Parsing Compressed Packets

In DNS, domain names inside the packet can sometimes be compressed to save space.
Instead of repeating full domain names, the DNS packet uses pointers to refer to earlier names.

A compression pointer has the two highest bits set (`11` in binary). The remaining 14 bits are an offset that points to another location in the packet where the full domain name starts.

When parsing, if a label length byte has the two highest bits set (i.e., `(length & 0xC0) == 0xC0`), it is a compression pointer.
We then extract the offset from the current two bytes, jump to that offset, and continue reading the domain name from there.

This ensures that we correctly reconstruct the full domain name while avoiding infinite loops by keeping track of visited positions. If multiple compression pointers are chained, we carefully handle them to avoid errors.

Parsing compressed packets correctly is critical, as many real DNS servers use compression to minimize packet size.

## Forwarding DNS Queries

If the DNS server cannot or does not want to directly answer a query, it can forward the query to an upstream resolver (e.g., Google's `8.8.8.8`) and relay the response back to the client.

The server acts as a middleman:

1. It receives the query from the client.
2. It sends the query to the resolver server.
3. It waits for a response with a timeout.
4. It sends back the resolver’s response to the client.

If there are multiple questions in the original query:

- Each question is forwarded separately.
- A new small query packet is created for each question.
- Each response is parsed to extract just the answer section.
- The server aggregates all answers and sends them back together in one combined response.

If the upstream resolver does not respond in time (timeout), the server sends a **default response** indicating an error.

This forwarding mechanism allows the server to work even without full DNS records of its own, behaving like a basic recursive resolver.
