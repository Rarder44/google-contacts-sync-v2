# Google Contacts Sync

Sync the contacts of a bunch of google accounts using the People API.

This script is an updated version of https://github.com/mrmattwilkins/google-contacts-sync.

All code has been rewritten.

# Features and improvements

- Synchronize groups and contacts much faster
- Synchronize photos of contacts
- Management of the simplified config
- Object-oriented programming that allows you to insert new features faster



## Setup

1. [Create a Google Cloud Platform project](https://console.cloud.google.com/projectselector2/iam-admin/serviceaccounts?supportedpurview=project&authuser=4).
   
   - at the top right click on "create project" and follow the guided instructions

2. Enable the people API
   - at the top left select the project you just created from the drop-down menu.
   - at the top left open the menu, click on "Api and Services" (if not visible check under the "other products" menu at the end of the "blocked" products
   - on the page that has just opened click (at the top of the page) on "+ Enable APIs and Services" search and enable "People API"

3. create JSON credentials
   - menu at the top left -> APIs and Services
   - menu on the left -> credentials
   - at the top of the page click on "+ Create credentials"
   - select OAuth client ID
   - (if this is your first time creating credentials in this project) you will be asked to define the OAuth Consent Screen:
      - if you use it in an organization choose "internal" otherwise "external"
      - fill in the fields and click on "create"
      - if you chose "external" you must give permission to those accounts to access via the API:
         - left menu -> OAuth consent screen
         - search for "Test Users" and click on "+ Add Users"
         - add the emails you want to sync
      - re-click on "+ Create credentials"
   - select OAuth client ID
   - select "Desktop Application" and click "create"
   - a popup appears where you can download the JSON\
      (if it does not appear in the "Credentials" screen you will find a new line with the arrow to download them)
   - Download the Json file and call it "GoogleAPI.json"

4. Install software

   ```
   pip3 install -r requirements.txt
   ```

5. Run the sync script

   ```
   python main.py
   ```

   it will create a default config file that you will need to edit.  The file will be included in the "configs" folder.

6. Copy the GoogleAPI.json file in the "configs" folder


7. Edit the config file.  You should have a tag for each of your accounts, this example is for three email addresses:
   myemail@gmail.com, otheremail@gmail.com, and anotheraccount@gmail.com.  It
   will look like this:

   ```
   [DEFAULT]
   last = 2023-10-04T13:14:06.002844+00:00
   backupdays = 7
   apijson_path = ./configs/GoogleAPI.json

   [account-myemail]
   user = myemail@gmail.com

   [account-otheremail]
   user = otheremail@gmail.com

   [account-anotheraccount]
   user = anotheraccount@gmail.com
   ```

   You don't need to edit the `last`, that gets updated when the script runs.\
   There should be no other things to set (for now)

8. The script needs to store the `credfile` tokens.\
   Run the script, a browser will be opened up for you to login as each of your accounts in turn and accept the access.\
   To avoid synchronization problems, in the console you will be told in which account to log in, once at a time.


9. Now you are ready to do syncing. 
   periodically start the "main.py" and the data will be synchronized.
   
   if this is the first time doing syncing then you will have to initialize things. 

   ### :warning: At the first start all contacts and groups are synchronized! There could be conflict problems on the names or the duplication of some contacts!
   
   If you have contacts, export in CSV or leave them on a single account, cancel all contacts from the other accounts.

   Make the first synchronization and then add all the contacts / groups you want.
   


## Adding another account ( WORK IN PROGRESS )
If you want to add another account, insert into the "config.ini" another account with the "new" key set to True:
```
[account-newAccount]
   user = newAccount@gmail.com
   new = True
```

### :warning: If the "new" key is not set, MANY CONTACTS WILL BE DELETED!

## parameters and particular features

TODO: 
