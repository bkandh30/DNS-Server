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
