import os
import pickle
import pathlib

from Google.Contact import Contact
from Google.Group import Group
from Google.Shared import Shared
from Google.SynchronizationLists import SynchronizationLists

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import google.auth.exceptions




class Account:
    def __init__(self,GoogleAPIjson_path, user):

        self.user=user
        self.contacts=[]
        self.groups=[]

        self.SyncListContacts=SynchronizationLists()
        self.SyncListGroups=SynchronizationLists()

        creds = None
        GoogleAPIjson_path = pathlib.Path(GoogleAPIjson_path)
        
        
        credfile = GoogleAPIjson_path.parent / f"key-{user}.save"

        #controllo se ho già salvato le credenziali da una vecchia autenticazione
        if credfile.exists():
            with open(credfile, 'rb') as token:
                creds = pickle.load(token)

        # se non sono valide -> re login
        if not creds or not creds.valid:

            #provo prima a fare il refresh delle credenziali
            managedToRefresh=False
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    managedToRefresh=True
                except google.auth.exceptions.RefreshError:
                    print("can't refresh token; relogin")

            #se non riesco -> faccio la login
            if not managedToRefresh:
                print("login into:", user)

                flow = InstalledAppFlow.from_client_secrets_file(
                    GoogleAPIjson_path, Shared.SCOPES
                )
                creds = flow.run_local_server(port=0,authorization_prompt_message="Login into: "+user)

            # Salvo le credenziali nel file corretto
            with open(credfile, 'wb') as token:
                pickle.dump(creds, token)


        self.GoogleService = build('people', 'v1', credentials=creds)

        self.pullContacts()
        self.pullGroups()



    def pullContacts(self):
        """scarica tutti i contatti dell'utente e se li salva internamente"""
        #fields=['names', 'organizations', 'clientData', 'metadata']

        # Keep getting 1000 connections until the nextPageToken becomes None
        connections_list = []
        next_page_token = ''
        while True:
            if not (next_page_token is None):
                # Call the People API
                results = self.GoogleService.people().connections().list(
                        resourceName='people/me',
                        pageSize=1000,
                        personFields=','.join(Shared.all_person_fields),
                        pageToken=next_page_token
                        ).execute()
                connections_list += results.get('connections', [])
                next_page_token = results.get('nextPageToken')
            else:
                break
        self.contacts =  [ Contact.fromGoogleObj(c,self) for c in connections_list ]

    
    def getContactBySyncTag(self,syncTag):
        return next((c for c in self.contacts if c.syncTag == syncTag),None)      #trova il primo o None
    def getContactByResourceName(self,resourceName):
        return next((c for c in self.contacts if c.resourceName == resourceName),None)      #trova il primo o None
    

    def getGroupBySyncTag(self,syncTag) -> Group:
        return next((g for g in self.groups if g.syncTag == syncTag),None)      #trova il primo o None 
    def getGroupByResourceName(self,resourceName):
        return next((g for g in self.groups if g.resourceName == resourceName),None)      #trova il primo o None
    def getGroupByID(self,ID):
        return next((g for g in self.groups if g.resourceName == f"contactGroups/{ID}"),None)      #trova il primo o None
    
    def getGroupsByResourceNames(self,*resourceNames):
        "ritorna un array di gruppi in base agli ID passati"
        return [g for g in self.groups if g.resourceName in resourceNames]

    def getGroupByName(self,name):
        return next((g for g in self.groups if g.name == name),None)      #trova il primo o None     

    def pullGroups(self):
        """scarica tutti i gruppi dell'utente e se li salva internamente"""
        # Keep getting 1000 connections until the nextPageToken becomes None
        ContactGroup_list = []
        next_page_token = ''
        while True:
            if not (next_page_token is None):
                # Call the People API
                results = self.GoogleService.contactGroups().list(
                        pageSize=1000,
                        groupFields=','.join(Shared.group_field),
                        pageToken=next_page_token
                        ).execute()
                ContactGroup_list += results.get('contactGroups', [])
                next_page_token = results.get('nextPageToken')
            else:
                break
        self.groups =  [ Group.fromGoogleObj(c,self) for c in ContactGroup_list if c["groupType"]=="USER_CONTACT_GROUP"]
        




    def applySyncListContacts(self):
        #aggiorno
        #cToUpdate:Contact
        #for cToUpdate in self.SyncListContacts.toUpdate:
        #    cToUpdate.update()

        self.batchUpdateContacts()


        #aggiungo
        #for cToAdd in self.SyncListContacts.toAdd:
            #gToAdd è un body
        #    tmp = Contact.create(cToAdd,self)

        self.batchCreateContacts()

        #cancello
        #for cToRemove in self.SyncListContacts.toRemove:
            #gToRemove è un syncTag
        #    c = self.getContactBySyncTag(cToRemove)
        #    if c:
        #        c.delete()

        self.batchRemoveContacts()


        if self.SyncListContacts.countAll>0:
            self.pullContacts()


        self.SyncListContacts=SynchronizationLists()

        


    def applySyncListGroups(self):

        #cancello
        for gToRemove in self.SyncListGroups.toRemove:
            #gToRemove è un syncTag
            g = self.getGroupBySyncTag(gToRemove)
            if g:
                g.delete()


        #aggiorno
        #se ci sono rinominazioni a catena ( esempio nomi:   a -> b | b -> c | c -> a ) c'è un deathlock!
        #quindi mi salvo in questo vettore tutti i gruppi che devo aggiornare in 2 fasi
        # 1) gli do un nome temporaneo ( li chiamo come il synctag cosi so che è univoco)
        # -) aggiorno tutti...
        # 2) aggiorno quelli con il nome temporaneo con il vero nome
        toUpdateLater=[]      
        allGroupsName=[group.name for group in self.groups]

        gToUpdate:Group
        for gToUpdate in self.SyncListGroups.toUpdate:
            if( gToUpdate.originalName!= gToUpdate.name and  gToUpdate.name in allGroupsName):
                #modifico temporaneamente il nome
                tmp = Group.fromGoogleObj(gToUpdate.cloneBody(),self)
                tmp.name=tmp.syncTag
                tmp.update()
                gToUpdate.etag=tmp.etag     #aggiorno l'etag per il successivo update

                toUpdateLater.append(gToUpdate)     #mi salvo per dopo il reale update
            else:
                gToUpdate.update()

        for gToUpdate in toUpdateLater:     #aggiorno tutti quelli che mi sono tenuto da parte
            gToUpdate.update()

        #aggiungo
        for gToAdd in self.SyncListGroups.toAdd:
            #gToAdd è un body
            tmp = Group.create(gToAdd,self)



        

        
        if self.SyncListGroups.countAll>0:
            self.pullGroups()

        self.SyncListGroups=SynchronizationLists()
            


    def batchUpdateContacts(self):

        #la batch puo al massimo aggiornare 200 contatti per singola request ( faccio 150 per sicurezza)
        l = self.SyncListContacts.toUpdate
        chunkSize=150
        contactsChunked=[ l[i:i + chunkSize] for i in range(0, len(l), chunkSize) ]

        for chunk in contactsChunked:

            contactsToUpdate = { contact.resourceName:contact.cloneBody() for contact in chunk }
            self.GoogleService.people().batchUpdateContacts(
                body={
                    "updateMask":','.join(Shared.all_update_person_fields),
                    "readMask":','.join(Shared.all_person_fields),
                    "contacts":{
                        **contactsToUpdate      
                    }
                }
            ).execute()

 
            
        

    def batchRemoveContacts(self):
        #la batch puo al massimo cancellare 500 contatti per singola request ( faccio 400 per sicurezza)
        l = self.SyncListContacts.toRemove
        chunkSize=400
        syncTagChunked=[ l[i:i + chunkSize] for i in range(0, len(l), chunkSize) ]

        for chunk in syncTagChunked:

            resourceNames = [ c.resourceName for c in self.contacts if c.syncTag in chunk]
            self.GoogleService.people().batchDeleteContacts(
                body={
                    "resourceNames":[
                        *resourceNames      
                    ]
                }
            ).execute()



    def batchCreateContacts(self):
        #la batch puo al massimo creare 200 contatti per singola request ( faccio 150 per sicurezza)
        l = self.SyncListContacts.toAdd
        chunkSize=150
        contactsChunked=[ l[i:i + chunkSize] for i in range(0, len(l), chunkSize) ]

        for chunk in contactsChunked:
            
            #tolgo i campi che non devo passare in fase di creazione
            cleanedContacts=[]
            for c in chunk:
                keysToDelete=["photos","resourceName","etag"]
                for k in keysToDelete:
                    if k in c:
                        c.pop(k)
                cleanedContacts.append(c)

            self.GoogleService.people().batchCreateContacts(
                body={
                    #"readMask":','.join(Shared.all_person_fields),
                    "contacts":[
                        #il formato fa schifo... ma è cosi...
                        *[ { "contactPerson":contact } for contact in cleanedContacts  ]
                    ]
                }
            ).execute()

