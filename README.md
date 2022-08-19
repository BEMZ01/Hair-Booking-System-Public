# Hair Booking System
![top language](https://img.shields.io/github/languages/top/BEMZ01/Hair-Booking-System-Public?style=for-the-badge)
![stars](https://img.shields.io/github/stars/BEMZ01/Hair-Booking-System-Public?style=for-the-badge)
![issues](https://img.shields.io/github/issues/BEMZ01/Hair-Booking-System-Public?style=for-the-badge)
![rate](https://img.shields.io/github/commit-activity/m/BEMZ01/Hair-Booking-System-Public?style=for-the-badge)
<br><br>
![GitHub code size in bytes](https://img.shields.io/github/languages/code-size/BEMZ01/Hair-Booking-System-Public?style=for-the-badge)

Est. 14/05/2021

A dedicated Hair Booking System featuring:
- Email System
- Google calendar sync 
- ~~(ical sync)~~ not going to be possible (apple bad)
- Intergrated login page
- Secure 

Built with ❤️ in [Flask](https://github.com/pallets/flask) and [Python 3](https://github.com/python)

<h1>Deployment</h1>
Want to deploy this yourself?
For now just run through replit.com

[Run on Repl.it](https://repl.it/badge/github/BEMZ01/ALevel-Hair)](https://repl.it/github/BEMZ01/Hair-Booking-System-Public)

<h1>Set-up (ez)</h1>
1. Clone the code<br>
2. Create Google project and enable Google calendar and CalDAV API's<br>
3. Create a client and server OAuth <br>
4. Download the keys and drop into the program's root folder.<br>


<h1>Set-up (step-by-step)</h1>
1. Download the code as ZIP<br>
2. Create a venv<br>
3. pip install -r requirements.txt<br>
4. Run app.py<br>
5. Go to [Google Cloud](https://console.developers.google.com/)<br>
6. Create a Project<br>
7. On the left panel select "Enabled API's and Services"<br>
8. Select Enable API's and Services and Search for Calendar<br>
9. Enable both Google Calendar API and CalDAV API by clicking on the Enable button<br>
10. On the left panel select OAuth Consent Screen<br>
11. Give you app a name, a support email and a logo (if desired)<br>
12. In the "Authorised domains" subsection, click Add domain then enter a website<br>
13. Click Save and Continue then "Add Scopes"<br>
14. Find "CalDAV API	.../auth/calendar.app.created" and "Google Calendar API	.../auth/calendar.freebusy" and enable them<br>
15. Click Save and Continue then add test users, only add the account you would like the calendar to show up in.<br>
16. Click Save and Continue then Back to Dashboard<br>
17. Enter the Credentials section<br>
18. Create Credientials -> OAuth client ID<br>
19. Application Type is Web Application<br>
20. Give you application a Name (same as before)<br>
21. Inside the Authorised JavaScript Origins section, add urls that will host the webserver, for example https://localhost or https://127.0.0.1<br>
22. Inside the Authorised redirect URL's add https://localhost:8000<br>
23. Create a new OAuth client ID <br>
23. Save the credentials, then Download OAuth Client for a "Desktop Client"<br>
24. Give the Desktop Client a name and click Create<br>
25. Click on Download JSON in the pop-up window<br>
26. Drop the file into the root of the program folder, then rename to "credentials.json"<br>
27. When starting the program, it may ask you to setup your google keys, if so restart the program.<br>
28. Open the URL in a browser or scan the QR code that is generated in the terminal and sign into the google account that will host the google calendar <br>
29. Copy the Authorisation code into the program, then press ENTER<br>
30. Once the program is done, you will get an IP in your console with an IP address, the server is now running and is now accessible at the address listed.<br>
