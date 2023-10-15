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
import json
import base64
from Utils.Logger import log

class Account:
    
    def __new__(cls,GoogleAPIjson_path, user,JSON=None):
        instance = super().__new__(cls)
        instance.contacts=[]
        instance.groups=[]
        instance.SyncListContacts=SynchronizationLists()
        instance.SyncListGroups=SynchronizationLists()


        return instance

    def __init__(self,GoogleAPIjson_path, user,JSON=None):
        """
        JSON = oggetto json che se impostato previene il download dei dati dal server ed inizializza le SyncList in modo da applicare direttamente un backup
        """

        self.user=user

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

        if JSON!=None:
            self.__importJSON(JSON)
        else:
            self.pullContacts()
            self.pullGroups()


    def fromBackup(backupObj):
        a=Account.__new__(Account,None,None,None) #non richiama la init

        for g in backupObj["groups"]:
            gg = Group.fromGoogleObj(g["body"],a)
            a.groups.append(gg)
            pass


        for c in backupObj["contacts"]:
            cc = Contact.fromGoogleObj(c["body"],a)
            if "photoBytes" in c:
                cc.photoCache = bytearray(base64.b64decode(c["photoBytes"]))
            a.contacts.append(cc)
            pass

        return a

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

        
        if self.SyncListContacts.countAll==0:
            return
    
        log("Contacts...")
        log.addIndentation(1)
        
        if len(self.SyncListContacts.toUpdate)>0:
           
            #aggiorno
            #cToUpdate:Contact
            #for cToUpdate in self.SyncListContacts.toUpdate:
            #    cToUpdate.update()
            log("update")
            log.addIndentation(1)
            self.batchUpdateContacts()
            log.addIndentation(-1)

        if len(self.SyncListContacts.toAdd)>0:
            #aggiungo
            #for cToAdd in self.SyncListContacts.toAdd:
                #gToAdd è un body
            #    tmp = Contact.create(cToAdd,self)

            log("create")
            log.addIndentation(1)
            self.batchCreateContacts()
            log.addIndentation(-1)


        if len(self.SyncListContacts.toRemove)>0:
            #cancello
            #for cToRemove in self.SyncListContacts.toRemove:
                #gToRemove è un syncTag
            #    c = self.getContactBySyncTag(cToRemove)
            #    if c:
            #        c.delete()

            log("remove")
            log.addIndentation(1)
            self.batchRemoveContacts()
            log.addIndentation(-1)


        #non lo faccio perchè se fatto troppo "presto" dopo un update o inserimento
        # non vengono recuperati i nuovi dati
        #if self.SyncListContacts.countAll>0:
        #    self.pullContacts()

        log.addIndentation(-1)
        self.SyncListContacts=SynchronizationLists()

        


    def applySyncListGroups(self):
        log("Groups...")
        log.addIndentation(1)

        if len(self.SyncListGroups.toRemove)>0:
            
            #cancello
            total=len(self.SyncListGroups.toRemove)
            n=0
            for gToRemove in self.SyncListGroups.toRemove:
                #gToRemove è un syncTag
                if gToRemove:
                    g = self.getGroupBySyncTag(gToRemove)
                    if not g: 
                        g = self.getGroupByResourceName(gToRemove)        #se per caso non è un sync, controllo se un resourceName #TODO: c'è un modo migliore?
                    
                    n+=1
                    log(f"remove {n}/{total}",end='\r')

                    if g:
                        g.delete()
            log(f"remove {n}/{total}")


        if len(self.SyncListGroups.toUpdate)>0:
            #aggiorno
            #se ci sono rinominazioni a catena ( esempio nomi:   a -> b | b -> c | c -> a ) c'è un deathlock!
            #quindi mi salvo in questo vettore tutti i gruppi che devo aggiornare in 2 fasi
            # 1) gli do un nome temporaneo ( li chiamo come il synctag cosi so che è univoco)
            # -) aggiorno tutti...
            # 2) aggiorno quelli con il nome temporaneo con il vero nome

            total=len(self.SyncListGroups.toUpdate)
            n=0

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
                    n+=1
                    log(f"update {n}/{total}",end='\r')

            for gToUpdate in toUpdateLater:     #aggiorno tutti quelli che mi sono tenuto da parte
                gToUpdate.update()
                n+=1
                log(f"update {n}/{total}",end='\r')
            log(f"update {n}/{total}")


        if len(self.SyncListGroups.toAdd)>0:
            #aggiungo   
            total=len(self.SyncListGroups.toAdd)
            n=0
            for gToAdd in self.SyncListGroups.toAdd:
                #gToAdd è un body
                tmp = Group.create(gToAdd,self)
                n+=1
                log(f"create {n}/{total}",end='\r')
            log(f"create {n}/{total}")

            if self.SyncListGroups.countAll>0:
                self.pullGroups()                   #TODO: controllo se davvero vengono ritornati! ( puo essere che non siano sincronizzati e devo usare i return delle funzioni)


        log.addIndentation(-1)
        self.SyncListGroups=SynchronizationLists()
            


    def batchUpdateContacts(self):

        #la batch puo al massimo aggiornare 200 contatti per singola request ( faccio 150 per sicurezza)
        l = self.SyncListContacts.toUpdate
        chunkSize=150
        contactsChunked=[ l[i:i + chunkSize] for i in range(0, len(l), chunkSize) ]

        numChunks=len(contactsChunked)
        n=0
        for chunk in contactsChunked:
            n+=1
            log(f"chunk: {n}/{numChunks}",end='\r')

            contactsToUpdate = { contact.resourceName:contact.cloneBody() for contact in chunk }

            for c in contactsToUpdate:
                c = contactsToUpdate[c]
                #rimuovo nomi gender e birthday duplicati
                #prendo il primo ( credo che gli altri vengano presi dal dominio... quindi magari messi in automatico.. bho!)
                if 'names' in c:
                    c['names'] = [c['names'][0]]
                if 'genders' in c:
                    c['genders'] = [c['genders'][0]]
                if "birthdays" in c:
                    c["birthdays"] = [c["birthdays"][0]]


            t=self.GoogleService.people().batchUpdateContacts(
                body={
                    "updateMask":','.join(Shared.all_update_person_fields),
                    "readMask":','.join(Shared.all_person_fields),
                    "contacts":{
                        **contactsToUpdate      
                    }
                }
            ).execute()
            for resourceName in t["updateResult"]:
                #TODO: controllo se l'inserimento della persona è andato a buon fine!
                # se non lo è, interrompo???
                updateStatus=t["updateResult"][resourceName]
                assert updateStatus["httpStatusCode"]==200,"Inserimento non andato a buon fine! Abort!"

                
                tmp=Contact.fromGoogleObj(updateStatus["person"],self)
                old = self.getContactBySyncTag(tmp.syncTag)
                old.copyFrom(tmp)
                old.updateTime=tmp.updateTime
        log(f"chunk: {n}/{numChunks}")
 
        

    def batchRemoveContacts(self):
        #la batch puo al massimo cancellare 500 contatti per singola request ( faccio 400 per sicurezza)
        l = self.SyncListContacts.toRemove
        chunkSize=400
        syncTagChunked=[ l[i:i + chunkSize] for i in range(0, len(l), chunkSize) ]

        numChunks=len(syncTagChunked)
        n=0
        for chunk in syncTagChunked:
            n+=1
            log(f"chunk: {n}/{numChunks}",end='\r')

            resourceNames = [ c.resourceName for c in self.contacts if c.syncTag in chunk or c.resourceName in chunk]       #l'or permette di passare anche i resourceName 
            self.GoogleService.people().batchDeleteContacts(
                body={
                    "resourceNames":[
                        *resourceNames      
                    ]
                }
            ).execute()

            for rn in resourceNames:
                self.contacts.remove(self.getContactByResourceName(rn))
            
        log(f"chunk: {n}/{numChunks}")

    def batchCreateContacts(self):
        #la batch puo al massimo creare 200 contatti per singola request ( faccio 150 per sicurezza)
        l = self.SyncListContacts.toAdd
        chunkSize=150
        contactsChunked=[ l[i:i + chunkSize] for i in range(0, len(l), chunkSize) ]

        numChunks=len(contactsChunked)
        n=0
        for chunk in contactsChunked:
            n+=1
            log(f"chunk: {n}/{numChunks}",end='\r')
            #tolgo i campi che non devo passare in fase di creazione
            cleanedContacts=[]
            for c in chunk:
                keysToDelete=["photos","resourceName","etag","coverPhotos"]
                for k in keysToDelete:
                    if k in c:
                        c.pop(k)

                #rimuovo nomi gender e birthday duplicati
                #prendo il primo ( credo che gli altri vengano presi dal dominio... quindi magari messi in automatico.. bho!)
                if 'names' in c:
                    c['names'] = [c['names'][0]]
                if 'genders' in c:
                    c['genders'] = [c['genders'][0]]
                if "birthdays" in c:
                    c["birthdays"] = [c["birthdays"][0]]
                    
                cleanedContacts.append(c)

          

            t = self.GoogleService.people().batchCreateContacts(
                body={
                    "readMask":','.join(Shared.all_person_fields),
                    "contacts":[
                        #il formato fa schifo... ma è cosi...
                        *[ { "contactPerson":contact } for contact in cleanedContacts  ]
                    ]
                }
            ).execute()
            for insertStatus in t["createdPeople"]:
                #TODO: controllo se l'inserimento della persona è andato a buon fine!
                # se non lo è, interrompo???
                assert insertStatus["httpStatusCode"]==200,"Inserimento non andato a buon fine! Abort!"

                tmp=Contact.fromGoogleObj(insertStatus["person"],self)
                self.contacts.append(tmp)

        log(f"chunk: {n}/{numChunks}")

            


        #TODO: prendere i dati ricevuti ed applicarli alla lista di contacts

    def exportJSON(self,includeImage=False):
        """crea un json object che contiene tutti i dati necessari per un backup"""
        obj={
                "groups":[ g.exportJSON() for g in self.groups],
                "contacts":[ c.exportJSON(includeImage) for c in self.contacts]
            }
        return obj

    def __importJSON(self,JSON):
        """dato il json( backup ) ad inizializzare le SyncList """

        #controllo se è un backup specifico ( con i resource name ) o generico ( solo syncTag)
        
        #generico
        #   cancello tutti i dati presenti sull'account
        #   sincronizzo tutti i gruppi ( popolo la SyncListGroup.toAdd e applico )
        #   prendo i gruppi appena inseriti
        #   sincronizzo tutti i contatti con relativi gruppi di appartenenza ( popolo la SyncListContacts.toAdd e applico )

        #specifico??? 

        #ci può essere inconsistenza! se ho un elemento con lo stesso SyncTag sia su server che su backup ma hanno resourceName differenti??
        # pulisco tutto ???
        #oppure
        #   creo un account temnporano con le stesse credenziali, come appoggio per ottenere e gestire i dati su server
        #   trovo:
        #    - i dati che ci sono già su server e vanno "aggiornati" ( uso il resourceName )
        #    - i dati che vanno cancellati su server
        #    - i dati che vanno inseriti su server
        



