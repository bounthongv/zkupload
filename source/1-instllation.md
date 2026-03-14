ZKTeco Attendance System Setup Manual



(ZKTime.Net + ZKBioTime + PostgreSQL + Device Integration)



This guide explains how to install and configure a ZKTime.Net and ZKBioTime system with a ZKTeco attendance device and access the attendance logs through PostgreSQL.



1\. System Requirements



Before starting:



Computer running Windows



Biometric device on the same network



Device IP address known



Installer packages available



Example installer location:



D:\\zktime-download\\



Packages used:



ZKTimenet\_4.1.3.4\_Thailand

ZKBioTime9.0.1 20240617.19506

2\. Install ZKTime.Net (Device Management Tool)



Run installer:



D:\\zktime-download\\ZKTimenet\_4.1.3.4\_Thailand



Follow installation wizard.



Registration information

User: boun

Password: 123456789

Email: bounthongv@gmail.com

3\. Add the Device in ZKTime.Net



After opening the software, add the device manually.



Example configuration:



Name: zk

IP Address: 192.168.100.180

Serial Number: CNYG242560011



You can find the IP address from the device menu:



Menu → Network → IP Address



Then:



Click Test Connection



Click Save



Important requirement:



The computer running ZKTime.Net must be in the same network as the device.



4\. Install ZKBioTime (Web Attendance System)



Run installer:



D:\\zktime-download\\ZKBioTime9.0.1 20240617.19506



During installation:



Web Port: 81

Database: PostgreSQL



Firewall must allow the selected port.



Example:



Allow TCP port 81

5\. Verify System Services



Open Windows service manager:



services.msc



Check that the following services are running:



bio-apache0

bio-cache

bio-monitor

bio-pgsql

bio-proxy

bio-redis

bio-server



These services control the entire ZKBioTime system.



6\. PostgreSQL Database Configuration



ZKBioTime automatically installs PostgreSQL.



Database configuration can be found here:



D:\\ZKBioTime\\attsite.ini



Example configuration:



\[DATABASE]

ENGINE=postgresql

NAME=biotime

USER=postgres

PASSWORD=@!@=XSY3CL6OIqr6sH0=

PORT=7496

HOST=127.0.0.1

7\. Access the Database



Use DBeaver to connect.



Connection parameters:



Host: 127.0.0.1

Port: 7496

Database: biotime

User: postgres

Password: (decoded value from attsite.ini)



Initially most tables will be empty because no device data has been received yet.



8\. Configure Device Push Communication



To allow the device to send attendance logs automatically:



Go to the device menu.



Menu → Communication → Network



Then configure:



Cloud Server Address = Computer IP

Server Port = 81



Example:



Server Address: 192.168.100.x

Port: 81

9\. Access the ZKBioTime Web System



Open a browser:



http://localhost:81



Login to the system.



10\. Device Auto Registration



After the device push configuration is correct:



The device will automatically appear in the system.



Menu:



Device → Device List



Status will show Auto Add.



However the device may show:



Area = Not Authorized

11\. Authorize the Device



Before the device can operate correctly, you must assign it to an area.



Step 1 – Create Area



Menu:



Access Control → Area



Create new area.



Example:



Area Name: Office

Parent Area: Root



Save.



Step 2 – Assign Area to Device



Menu:



Device → Device List



Click the Auto Add device.



Assign the newly created area.



Save.



Now the device becomes Authorized.



12\. Device Synchronization



After authorization:



The device will begin syncing with the server automatically.



Attendance punches will be pushed to the server.



13\. Verify Attendance Logs in Database



Open the database using DBeaver.



Run:



SELECT \*

FROM iclock\_transaction

ORDER BY punch\_time DESC;



This table contains raw attendance logs from the device.



Important fields include:



Column	Description

emp\_code	Employee ID

punch\_time	Time of attendance

punch\_state	IN / OUT

verify\_type	Fingerprint / Face / Card

terminal\_sn	Device serial number



Once the device sends logs, records will appear here automatically.



14\. System Architecture



The data flow works as follows:



ZKTeco Device

&#x20;       ↓

Push Attendance Data

&#x20;       ↓

ZKBioTime Web Server

&#x20;       ↓

PostgreSQL Database

&#x20;       ↓

Table: iclock\_transaction

15\. Future Plan (Cloud Integration)



The goal is to build a cloud attendance database.



Proposed approach:



Local ZKBioTime Database

&#x20;       ↓

Extract attendance logs

&#x20;       ↓

Push to Cloud Database



Initial design:



Cloud Table:

iclock\_transaction



Additional tables can be added later if needed (for example employee data).



16\. Key Table for Integration



Main table used for attendance integration:



iclock\_transaction



This table contains all raw device punch records.



It is usually sufficient for most attendance systems.



✅ This manual now documents the entire setup workflow, so you can easily reproduce the system later.



If you'd like, I can also help you create a much better architecture for your cloud plan, because pushing iclock\_transaction directly has two common problems (duplicates and missing punches) that many integrators run into. I can show you the safer design used in large deployments.

