# DNS Server Implementation

The DNS server works on **UDP Protocol** at `PORT: 53`.

To query the DNS servers on your own terminal, you can use the `dig` (Domain Information Groper) command. It provides detailed information about domain names, IP addresses, and DNS records.

```bash
dig google.com
```

If it gives a timeout error, it means your network's default server is broken or slow. Try specifying a resolver manually:

```bash
dig google.com @8.8.8.8
```

Example output:

```
; <<>> DiG 9.10.6 <<>> google.com @8.8.8.8
;; global options: +cmd
;; Got answer:
;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 6484
;; flags: qr rd ra; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 1

;; OPT PSEUDOSECTION:
; EDNS: version: 0, flags:; udp: 512
;; QUESTION SECTION:
;google.com.\t\t\tIN\tA

;; ANSWER SECTION:
google.com.\t\t147\tIN\tA\t142.250.72.142

;; Query time: 44 msec
;; SERVER: 8.8.8.8#53(8.8.8.8)
;; WHEN: Thu Apr 03 21:36:57 MST 2025
;; MSG SIZE  rcvd: 55
```

---

## Table of Contents

- [Protocols](#protocols)
- [Message](#message)
- [Header Section Structure](#header-section-structure)
- [Question Section Structure](#question-section-structure)
- [Answer Section Structure](#answer-section-structure)
- [Parsing the Header Section](#parsing-the-header-section)
- [Parsing Question Section](#parsing-question-section)
- [Parsing Compressed Packets](#parsing-compressed-packets)
- [Forwarding DNS Queries](#forwarding-dns-queries)

---

## Protocols

DNS is built on **UDP (User Datagram Protocol)** because:

- UDP is **connectionless** — it sends packets without a handshake and has lower overhead than TCP.
- It is ideal for sending small amounts of data quickly without the complexity of TCP.
- It scales well for the massive number of DNS queries happening worldwide every second.
- Each DNS request is independent, making stateless protocols like UDP simpler and faster for servers.

However, if a DNS response exceeds **512 bytes**, it falls back to **TCP** to handle the larger response. Certain operations (like zone transfers) also require TCP.

---

## Message

All communications in the DNS protocol are carried in a single format called a **message**.  
Each message consists of **5 sections**:

- Header
- Question
- Answer
- Authority
- Additional

Domain names inside DNS packets are encoded as a sequence of **labels**.

Each label is encoded as `<length><content>`, where:

- `<length>` is a single byte indicating the length of the label.
- `<content>` is the actual text of the label.

The sequence of labels is terminated by a null byte (`\x00`).

---

## Header Section Structure

The header section controls the content of the other four sections.

It consists of the following fields (each 16 bits long):

- Identification
- Flags
- Number of Questions
- Number of Answers
- Number of Authority RRs
- Number of Additional RRs

The identification field is used to match responses with queries. After the flags word, the header ends with four 16-bit integers, one for each following section.

---

## Question Section Structure

The **question section** contains a list of questions (usually just one) that the client wants answered.  
Each question has:

- **Name**: A domain name, represented as a sequence of labels.
- **Type**: The type of record (e.g., A, AAAA, MX).
- **Class**: Usually set to 1 (for Internet).

---

## Answer Section Structure

The **answer section** contains a list of **resource records** (RRs), which are answers to the questions.

Each RR includes:

- Name
- Type
- Class
- TTL (Time to Live)
- Data Length
- Data

**TTL** specifies how long the response can be cached before being re-queried.

---

## Parsing the Header Section

When parsing the DNS packet:

- The first two bytes are the **Query ID**.
- **Flags** are the next two bytes:
  - **OPCODE** is extracted by shifting the flags 11 bits to the right and masking with `0xF`.
  - **RD (Recursion Desired) flag** is extracted by shifting the flags 8 bits to the right and masking with `0x1`.

From these, we extract the Query ID, OPCODE, and RD flag.

We then build the response flags:

- Start with `0x8000` (sets QR bit to 1, marking it as a response).
- Add the same OPCODE (shifted 11 bits left).
- Add the RD flag (shifted 8 bits left).
- Set the RCODE:
  - `0` if standard query.
  - `4` (Not Implemented) for unsupported opcodes.

The RCODE is incorporated into the lowest 4 bits of the response flags.

---

## Parsing Question Section

To parse the question section:

- **Skip the first 12 bytes** (header).
- The domain name is parsed:
  - Read a byte to determine the length.
  - Read that many bytes as label content.
  - Repeat until a `0x00` byte is encountered, indicating the end.
- After the domain name:
  - Read 2 bytes for the **Type**.
  - Read 2 bytes for the **Class**.

The question section is reconstructed by concatenating the extracted domain name, type, and class bytes.

---

## Parsing Compressed Packets

In DNS, domain names can be **compressed** to save space.  
Instead of repeating domain names fully, the packet may use **pointers** to earlier labels.

- A compression pointer has the two highest bits set (`11`).
- The remaining 14 bits specify the **offset** to the original domain name.

When parsing:

- If a label length byte has the top two bits set, it is a pointer.
- Extract the offset, jump to that position, and continue parsing.
- Avoid infinite loops by keeping track of visited positions.

Parsing compression correctly is essential because most real DNS servers use it heavily.

---

## Forwarding DNS Queries

If the DNS server does not have an answer, it can **forward** the query to an upstream resolver (e.g., `8.8.8.8`) and relay the response back.

Forwarding steps:

1. Receive the query from the client.
2. Send it to the upstream resolver.
3. Wait for a response (with timeout handling).
4. Send the resolver's response back to the client.

If the original query contains **multiple questions**:

- Each question is forwarded separately.
- New small query packets are generated.
- Each response is parsed for just the answer section.
- Answers are combined into a single response packet.

If the upstream resolver does not respond in time, the server sends a **default error response**.

This forwarding behavior allows the DNS server to work without maintaining its own full database of domain records.

---
