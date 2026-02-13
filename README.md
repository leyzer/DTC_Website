CS50 final project

# Warhammer 40k League
#### Video Demo:  <URL https://youtu.be/r7avI54Kof4>
#### Description:
<h3>general overview:</h3>
<p>I decided to create a digitize version of my local Warhammer 40k clubs league.
The goal was to make the statistics easier to see as well as allow easy access to interesting statistics similar to those shown in large scale online events.</p>
<p>In the league, a player's score out of 100 comprises three main categories: Generalship, Hobby, and Social. The Generalship score, contributing 40 points, is determined by a ranking system where the leader receives the maximum points and others receive points relative to their proximity to the leader. The Hobby score, worth 20 points, is divided into Painting and WYSIWYG (What You See Is What You Get), each contributing 10 points. These scores are based on the percentage of games played fully painted or WYSIWYG. The Social score, also worth 40 points, is further divided into Games Played and Unique Opponents, with 10 and 30 points respectively. The former is based on the percentage of games played relative to others, while the latter depends on the number of different opponents a player faces. These scoring mechanisms aim to promote painted armies, authentic gameplay, and encourage players to engage socially by playing against a variety of opponents</p><p>Each of the catagories are set up as global variables in the server.py in preparation of future changes.

<p>The General league involves players playing games against other members of the club. 
Each game is recorded with the following details:
<ul>Players Names</ul> 
<ul>Armies Selected</ul>
<ul>Date</ul>
<ul>Both players painted status</ul>
<ul>Both players WYSIWYG(wht you see is what you get) status</ul>
<ul>Game Result</ul>
</p>
    
 
<h3>Overall Screen/Home Page:</h3>
<p>The home page defaults to the current Season with the option of a drop down to see past seasons or the entire league to date.
 Once players have played 10 or more games they are highlighted green to show that they are qualified for that years awards.
<br>
<h3>Games Played:</h3>
<p>Games played shows each game Date, player names, score and if it has been verified. I decided on a check box to display the different stages (unverified, verified and disabled).
Only Admins can verify the games so the check boxes are disabled/Greyed out for non admins. The list is organised with latest games on the top and with winners(player who gained points) on the left. In the case of a draw the player with the lower starting score would gain 1/2 the points they would have in a win and the other player loses those points</p><p>Only games from the current season can be verifed and the points scores are worked out on a first in first out order.</p>

<br>
<h3>Add Results:</h3>
<p>The date is selected using a date picker to guaranted that the format is correct. Player one is locked to the logged in user unless that user is an admin. Date, players, factions and results are required inorder to submit results</p>

<br>
<h3>Faction Stats:</h3>
<p>Faction stats was the section I was most excited about as it allowed me to generate graphs to visualise the faction breakdowns as was not posible before. Once again the page defaults to the current year but can be selected with a drop down menu. The graph displays all used factions with a percentage of the whole.</p>

<br>
<h3>Player Stats:</h3>
<p>Player stats similarly to "faction stats" player stats shows each faction and its varies stats alongside a graph. Its default is the active user and the current Season. All players and year combinations are available to view</p>

<br>
<h3>About:</h3>
<p>This was added to have an easy way to show the required into the video when using windows screen record</p>

<br>
<h3>My Profile:</h3>
<p>This allowed a space to show the usual account info as well as allowed the resetting of passwords if needed. 
This allowed a location for Admin to give and take admin rights away from users as well as progress to the next season. 
Ending the season using the button updated all the users Generalship tables as well as adjusted the current year</p>

<br>
<h3>Register:</h3>
<p>This is a basic registration page it requires a unique username and email. The first and last name are capitalized and the username and email are saved in lowercase. </p>

<br>
<h3>Login/Logout</h3>
<p>This is standard to most websites the user name is used to login</p>

<br>
<h2>files:</h2>
<h3> styles.css</h3>
<p>I went quite basic with the CSS. Choosing to change the fonts used as well as adjusting how the tables showed up and were grouped. Bootstrap and some Google Apis were linked to simplifiy adjusting the tables and fonts </p>

<br>
<h3>helpers.py</h3>
<p>This file was used to store functions used to help simplify the server file.</p>
<br>
<h3>Javascript in htmls</h3>
<p>I went with the simpler built in JS as all I needed it for was the drop down menus as well as graphs on the stats pages </p>

<h3>server.py</h3>
<p>The code for loading each page is included in server.py</p>

<h2>SQL database</h2>
<p>The SQL database is split into factions,games,generalship,rating_table,results, season and users. I took this approach to reduce the about of duplications and to make adjusting details quicker if the need arose. The set up also assisted in making pulling reports on the info easier inside the python file</p>
<p>The generalship keeps track the users for each season and is expanded at the beginning of each season</p>
<p>Games record each individual game whilre results records each players details for there game</p>
<p>Factions and ratings table contain the base reference items, and shouldn't need to be updated unless changes are needed.</p>
<p>Season records the leagues year and so only gets updated once a year for as long as the league runs</p>
<p>Users is where every player who logins into the system is recorded</p>



