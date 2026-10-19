---
layout: post
lang: en
ref: gioi-thieu-ve-internet
author: Ming Chen
title: "Explaining the Internet"
tags: [backend-production]
description: "What the Internet is and how it works — the last mile, data centers and the backbone — plus applications like the web and email."
---

>The Internet is the most popular computer network in the world. It started as an academic research project in 1969 and grew into a global commercial network in the 1990s. ![Portrait of Al Gore](/assets/img/2022-12-25-gioi-thieu-ve-internet/al-gore.jpg "Photo: official portrait, public domain")

## What is the Internet?

The Internet is the most popular computer network in the world. It started as an academic research project in 1969 and grew into a global commercial network in the 1990s. Today it is used by more than 4.9 billion people around the world.

The Internet is remarkable for its decentralization. Nobody owns the Internet or controls who can connect to it. Instead, thousands of different organizations operate their own networks and negotiate voluntary interconnection agreements.

Most people access Internet content with a web browser. Indeed, the web has become so popular that many people wrongly treat the Internet and the web as synonyms. But in reality the web is just one of many Internet applications. Other popular Internet applications include email and BitTorrent.

## Where is the Internet?

The Internet has 3 basic parts:

1) The "last mile" is the part of the Internet that connects homes and small businesses to the Internet. Right now, about 60% of residential Internet connections in the US are provided by cable TV companies like Comcast and Time Warner. Of the remaining 40%, a growing share uses new fiber-optic cable — most of it part of Verizon's FiOS program or AT&T's U-Verse. Finally, a significant but shrinking number still uses outdated DSL service delivered over telephone lines.
The last mile also includes the towers that let people access the Internet from their mobile phones. Wireless Internet service accounts for a large and growing share of all Internet use.
![Diagram of the last-mile connection from your home to the carrier](/assets/img/2022-12-25-gioi-thieu-ve-internet/last-mile.jpg)

2) Data centers are rooms full of servers that store user data and host online applications and content. Some are owned by large companies like Google and Meta. Others are commercial facilities serving many smaller websites. Data centers have very fast Internet connections, so they can serve many users at the same time. Data centers can sit anywhere in the world, but they are often placed in remote regions where land and electricity are cheap. For example, Google, Meta and Microsoft have all built sprawling data centers in Iowa.
![Illustration of server racks inside a data center](/assets/img/2022-12-25-gioi-thieu-ve-internet/data-center.jpg)

3) The Internet backbone consists of long-distance networks, mostly over fiber-optic cable, carrying data between data centers and consumers. The backbone market is highly competitive. Backbone providers typically connect their networks at Internet exchange points, usually located in large cities. Establishing a presence at an IXP makes it much easier for backbone providers to improve their connectivity with one another.
![Diagram of the fiber backbone connecting data centers through exchange points](/assets/img/2022-12-25-gioi-thieu-ve-internet/duong-truc-backbone.jpg)

## Who created the Internet?

The Internet began as ARPANET, an academic research network funded by the military's Advanced Research Projects Agency (ARPA, now DARPA). The project was led by Bob Taylor, an ARPA administrator, and the network was built by the consulting firm Bolt, Beranek and Newman. It went live in 1969.

In 1973, software engineers Vint Cerf and Bob Kahn started working on the next generation of networking standards for ARPANET. These standards, called TCP/IP, became the foundation of the modern Internet; ARPANET switched to TCP/IP on January 1, 1983.
![Vint Cerf and Bob Kahn receiving the Medal of Freedom](/assets/img/2022-12-25-gioi-thieu-ve-internet/vint-cerf-bob-kahn.jpg "Photo: White House, public domain")
In the 1980s, funding for the Internet shifted from the military to the National Science Foundation (NSF). The NSF funded the long-distance networks that served as the Internet's backbone from 1981 to 1994. In 1994, the Clinton administration handed control of the Internet backbone to the private sector. It has been privately operated and funded ever since.

## Did Al Gore (the 45th US Vice President) invent the Internet?

Former Vice President Al Gore is often quoted as claiming credit for inventing the Internet. But what he actually said in a 1999 CNN interview was "I took the initiative in creating the Internet." Gore was widely mocked for this claim. But the people who invented the Internet — TCP/IP designers Bob Kahn and Vint Cerf — wrote in his defense in 2000. They argued that Gore was "the first political leader to recognize the importance of the Internet and to promote and support its development."
![Portrait of Al Gore](/assets/img/2022-12-25-gioi-thieu-ve-internet/al-gore.jpg "Photo: official portrait, public domain")
"As far back as the 1970s Congressman Gore promoted the idea of high-speed telecommunications," the pair wrote. "As a Senator in the 1980s, Gore urged government agencies to consolidate what were then dozens of different and unconnected networks into an 'inter-agency network'." One of the main vehicles was to spread the Internet beyond the field of computer science.

## Who runs the Internet?

Nobody runs the Internet. It is organized as a decentralized network of networks. Thousands of companies, schools, governments and other entities operate their own networks and exchange traffic with one another based on voluntary interconnection agreements.
The shared technical standards that make the Internet work are managed by an organization called the Internet Engineering Task Force (IETF). The IETF is an open organization; anyone is free to attend meetings, propose new standards and suggest changes to existing ones. Nobody is forced to adopt IETF-endorsed standards, but the IETF's consensus-based decision process helps ensure its recommendations are usually accepted by the Internet community.
![Illustration of how the IETF builds open standards](/assets/img/2022-12-25-gioi-thieu-ve-internet/ietf-tieu-chuan.jpg)
The Internet Corporation for Assigned Names and Numbers (ICANN) is sometimes described as responsible for Internet governance. As its name suggests, ICANN is responsible for distributing domain names (like mingchen.id.vn) and IP addresses. But ICANN does not control who can connect to the Internet or what kind of information may be sent over it.
![Illustration of ICANN's role coordinating domain names and IP addresses](/assets/img/2022-12-25-gioi-thieu-ve-internet/icann-ten-mien-ip.jpg)

## What is an IP address?

Internet Protocol addresses are the numbers computers use to identify one another on the Internet. For example, the IP address of vox.com is 216.146.46.10. ICANN's division called the Internet Assigned Numbers Authority is responsible for distributing IP addresses so that two different organizations never use the same address.
![Illustration of how to look up an IP address on a computer](/assets/img/2022-12-25-gioi-thieu-ve-internet/dia-chi-ip.jpg)

## What is IPv6?

![Diagram of the IPv6 address structure](/assets/img/2022-12-25-gioi-thieu-ve-internet/ipv6.jpg)
The current Internet standard, called IPv4, allows only about 4 billion IP addresses. That seemed like a huge number in the 1970s, but today the supply of IPv4 addresses is nearly exhausted.

So Internet engineers developed a new standard called IPv6. IPv6 allows an astonishing number of unique addresses — the exact figure is 39 digits long — ensuring the world will never run out again.

At first, the transition to IPv6 was slow. The technical work on the standard was finished in the 1990s, but the Internet community faced a serious chicken-and-egg problem: as long as most people used IPv4, there was little incentive for anyone to switch to IPv6.

But as IPv4 addresses grew scarce, IPv6 adoption accelerated. The share of users connecting to Google over IPv6 rose from 1% in early 2013 to 6% by mid-2015.

## How does wireless Internet work?

In the early years, Internet access traveled over physical cables. But recently, wireless Internet access has become increasingly popular.

There are two basic kinds of wireless Internet access: Wi-Fi and cellular. Wi-Fi networks are relatively simple. Anyone can buy Wi-Fi networking gear to provide Internet access in a home or business. Wi-Fi networks use unlicensed spectrum: electromagnetic frequencies available for anyone to use for free. To stop neighbors' networks from interfering with each other, there are strict limits on the power (range) of Wi-Fi networks.
![Diagram of a home Wi-Fi network](/assets/img/2022-12-25-gioi-thieu-ve-internet/wifi-tai-nha.jpg)

Cellular networks are more centralized. They work by dividing the service area into cells. In the most crowded areas, cells can be as small as a city block; in rural areas a cell can stretch for miles. Each cell has a tower at its center serving the devices in it. When a device moves from one cell to another, the network automatically hands the device from one tower to the next, letting users keep communicating without interruption.
![Diagram of a cellular network divided into cells](/assets/img/2022-12-25-gioi-thieu-ve-internet/mang-di-dong.jpg)
Cells are too large to use the low-power, unlicensed spectrum of Wi-Fi networks. Instead, cellular networks use spectrum licensed for their exclusive use. Because this spectrum is scarce, it is usually awarded by auction. Wireless auctions have generated tens of billions of dollars for the US Treasury since they were first held in 1994.

## What is the cloud?

![Diagram of cloud computing](/assets/img/2022-12-25-gioi-thieu-ve-internet/dien-toan-dam-may.jpg)
Cloud computing describes an approach to computing that became popular in the early 2000s. By storing files on servers and delivering software over the Internet, cloud computing gives users a simpler, more reliable computing experience. Cloud computing lets consumers and businesses treat computing as a utility, leaving the technical details to technology companies.
For example, in the 1990s many people used MS Office to edit documents and spreadsheets. They stored documents on their hard drives, and when a new version of MS Office was released, customers had to buy it and manually install it on their PCs.
Google Docs, by contrast, is a cloud office suite. When users visit docs.google.com, they automatically get the newest version of Google Docs. Because their files are stored on Google's machines, the files are available on every computer. Even better, users never have to worry about losing their files when a hard drive fails (M$ now has its own cloud office suite called Office 365).
There are plenty of other examples. Gmail and Hotmail are cloud email services that largely replaced desktop email apps like Outlook. Dropbox is a cloud computing service that automatically syncs data across devices, freeing people from carrying files around on floppy disks. Apple's iCloud automatically copies users' music and other files from the desktop to their mobile devices, sparing users the hassle of syncing over a USB connection.
Cloud computing has also had a big impact on businesses. In the 1990s, companies that wanted to create a website had to buy and operate their own servers. But in 2006, Amazon.com launched Amazon Web Services, letting customers rent servers by the hour. That lowered the barrier to creating a website and made it much easier for sites to scale up capacity quickly as they grew more popular.

## What is a packet?

A packet is the basic unit of information transmitted over the Internet. Splitting information into small, easy-to-digest pieces allows the network's capacity to be used more efficiently.
A packet has two parts. The header holds information that helps the packet reach its destination: the packet's length, its source and destination, and a checksum value that helps the receiver detect whether the packet was damaged in transit. After the header comes the actual data. A packet can hold 64KB of data, equivalent to about 20 pages of plain text.
If Internet routers run into congestion or other technical problems, they are allowed to solve the problem by dropping packets. It is the sending computer's job to notice that a packet never arrived and send another copy. This approach may seem counterintuitive. But it simplifies the Internet's core infrastructure, delivering higher performance at lower cost.

## What is the World Wide Web?

The World Wide Web is a popular way to publish information on the Internet. The web was created by Timothy Berners-Lee, a computer programmer at the European scientific research organization CERN, in 1991. It provided a more powerful and user-friendly interface than other Internet applications. The web supports hyperlinks, letting users browse from one document to another with a single click.
![Tim Berners-Lee, father of the World Wide Web](/assets/img/2022-12-25-gioi-thieu-ve-internet/tim-berners-lee.jpg "Photo: Enrique Dans, CC BY 2.0")
Over time, the web grew ever more sophisticated, supporting images, audio, video and interactive content. By the mid-1990s, companies like Yahoo and Amazon had started building profitable businesses on the web. In the 2000s, full-featured web-based applications like Yahoo Maps and Google Docs were created.
In 1994, Berners-Lee founded the World Wide Web Consortium (W3C) to serve as the web's official standards body. He remains the W3C's director and continues to oversee the development of web standards. The web is an open platform, however, and the W3C cannot force anyone to accept its proposals. In practice, the organizations with the most influence over the web are M$, Google, Apple and Mozilla, the makers of the leading web browsers. Any technology adopted by these four companies becomes a de facto web standard.
The web has become so popular that many people now treat it as synonymous with the Internet itself. But technically, the web is just one of many Internet applications. Other applications include email and BitTorrent.

## What is a web browser?

A web browser is a computer program that lets users download and view web pages. Browsers are available for desktops, tablets and mobile phones.
![Illustration of the Mosaic browser in 1993](/assets/img/2022-12-25-gioi-thieu-ve-internet/trinh-duyet-dau-tien.jpg)
The first widely used browser was Mosaic, created by researchers at the University of Illinois. The Mosaic team moved to California to found Netscape, which built the first commercially successful web browser in 1994.
![Recreation of the Mosaic browser window](/assets/img/2022-12-25-gioi-thieu-ve-internet/mosaic-minh-hoa.jpg)
![Recreation of the Netscape Navigator browser](/assets/img/2022-12-25-gioi-thieu-ve-internet/netscape-minh-hoa.jpg)
Netscape's popularity was soon eclipsed by M$'s IE, but an open-source version of the Netscape browser became the modern Firefox browser. Apple released the Safari browser in 2003, and Google released a browser called Chrome in 2008. By 2015, Chrome had become the most popular web browser with a 50% market share, while IE, Firefox and Safari also held significant shares.
![Timeline of web browsers](/assets/img/2022-12-25-gioi-thieu-ve-internet/cuoc-dua-trinh-duyet.jpg)

## What is SSL?

SSL stands for Secure Sockets Layer, a family of encryption technologies that lets web users protect the privacy of the information they transmit over the Internet.
When you visit a secure website such as gmail.com, you see a padlock next to the URL. It indicates that your communication with the site is encrypted. Here is what the interface looks like in Google's Chrome browser.
![Illustration of the HTTPS padlock and an encrypted connection](/assets/img/2022-12-25-gioi-thieu-ve-internet/ssl-https.jpg)

That padlock is supposed to signal that third parties cannot read any information you send or receive. Basically, SSL does this by turning your data into an encrypted message that only the recipient knows how to decode. If a malicious party is listening in on the conversation, it sees only a seemingly random string of characters — not your email content, Facebook posts, credit card numbers or other personal information.
SSL was introduced by Netscape in 1994. In the early years it was used only on certain kinds of sites, such as online banking websites. In the early 2010s, Google, Yahoo and Facebook all used SSL encryption for their websites and online services. More recently, there has been a movement toward universal SSL. In 2015, Mozilla announced that future versions of the Firefox browser would treat the lack of SSL encryption as a security bug, as a way to push every website to upgrade. Google was considering doing the same with Chrome.

## What is DNS?

DNS — the Domain Name System — is the reason you can reach mingchen by typing mingchen.id.vn into your browser instead of a hard-to-remember numeric address like 216.146.46.10.
The system is hierarchical. For example, .com domains are managed by a company called Verisign. Verisign assigns subdomains like google.com and facebook.com. In turn, the owners of these second-level domains can create subdomains like mail.google.com and maps.google.com.
Because popular websites use domain names to identify themselves publicly, DNS security has become a growing concern. Criminals as well as government spies have tried to compromise DNS to impersonate popular sites like facebook.com and gmail.com and intercept their private communications. A standard called DNSSEC seeks to strengthen DNS security with encryption, but few have adopted it.
![Diagram of the DNS domain name hierarchy](/assets/img/2022-12-25-gioi-thieu-ve-internet/dns.jpg)

## Who decides which domain names exist and who gets them?

The domain name system is managed by ICANN — a California-based nonprofit. ICANN was founded in 1998. It was granted authority over DNS by the US Department of Commerce, although it has increasingly asserted its independence from the US government.
There are two kinds of domain names. First are generic top-level domains (gTLDs), such as .com, .edu, .org and .gov. Because the Internet originated in the US, these domains tend to be most popular there. Authority over these domains is usually delegated to private organizations.
![Illustration of generic top-level domains](/assets/img/2022-12-25-gioi-thieu-ve-internet/ten-mien-gtld.jpg)
Then there are country-code top-level domains (ccTLDs). Every country in the world has its own 2-letter code — the US ccTLD is .us, the UK's is .uk, China's is .cn. These domains are managed by authorities in each country. Some ccTLDs, such as .tv (for the island nation of Tuvalu) and .io (British Indian Ocean Territory), have become popular for use outside their own countries.
![Illustration of country-code top-level domains](/assets/img/2022-12-25-gioi-thieu-ve-internet/ten-mien-cctld.jpg)
In 2011, ICANN voted to make it easier to create new gTLDs. As a result, there may be dozens or even hundreds of new domains in the next few years.

## Source

[Vox](https://www.vox.com/2014/6/16/18076282/the-internet)

*Photo credits: the Al Gore photo is the official portrait of the US Vice President (1994, public domain); the Vint Cerf and Bob Kahn photo is a White House photo by Paul Morse (2005, public domain); the Tim Berners-Lee photo is by Enrique Dans ([CC BY 2.0](https://creativecommons.org/licenses/by/2.0/)) — all three via Wikimedia Commons. The remaining diagrams are my own.*
