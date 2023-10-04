import random
import string
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import google.auth.exceptions
import requests

from Google.Account import Account
from Google.Group import Group
from Google.Contact import Contact
from ConfigManager import ConfigManager

from Utils.Logger import log



class SyncManager:
    """
    permette di gestire una serie di account e di sincronizzarli tra loro
    """

    def __init__(self,configurations) -> None:
        self.__accounts=[]
        self.__temporaryReservedSyncTag=[]      #quando viene creato un sync, fino a che non viene applicato devo tenerlo in memoria per evitare duplicati
        self.__configurations:ConfigManager=configurations

    def addAccount(self, account):
        self.__accounts.append(account)
    def removeAccount(self,account):
        self.__accounts.remove(account)

    
    def pull(self):
        """riscarica tutti i dati da tutti gli account"""
        a:Account
        for a in self.accounts:
            a.pullGroups()
            a.pullContacts()
        
        

    def getContactBySyncTag(self,syncTag):
        """ritorna il primo contatto con il syncTag specificato, se non viene trovato, ritorna None"""
        for a in self.__accounts:
            #a:Account=a
            c =a.getContactBySyncTag(syncTag)
            if c:
                return c
        return None

    def getGroupBySyncTag(self,syncTag):
        """ritorna il primo gruppo con il syncTag specificato, se non viene trovato, ritorna None"""
        for a in self.__accounts:
            #a:Account=a
            g =a.getGroupBySyncTag(syncTag)
            if g:
                return g
        return None

    def syncTagExist(self,syncTag):
        if self.getContactBySyncTag(syncTag)!= None:
            return True
        if self.getGroupBySyncTag(syncTag)!= None:
            return True
        return False
    
    def getOtherAccounts(self,Account):
        """ritorna la lista di Accout diversi da quelli passato"""
        return [x for x in self.__accounts if x != Account]
    
    



    def syncGroups(self):
        
        log("identifico i gruppi da syncronizzare...")
        toDelete=0
        toUpdate=0
        toAdd=0
        #recupero tutti i gruppi che hanno un sync e li metto in "comune"
        commonGroups={}
        for account in self.__accounts: 
            for g in account.groups:
                if g.syncTag!=None:
                    if not g.syncTag in commonGroups:
                        commonGroups[g.syncTag]=[]
                    commonGroups[g.syncTag].append(g)

        #-------------------------
        #--- gruppo cancellato ---
        #-------------------------

        #cerco tutti quei gruppi che non li trovo "N" volte all'interno di ogni vettore di syncTag 
        #( se un utente cancella un gruppo, dovrei vedere che non tutti gli account hanno quel determinato gruppo)
        numAccounts=len(self.__accounts)

        groupsToDelete= { syncTag:commonGroups[syncTag] for syncTag in commonGroups if len(commonGroups[syncTag])<numAccounts }
        toDelete = len(groupsToDelete)


        for syncTag in groupsToDelete:
            
            #dovrebbe essere meno ottimizzato ma sicuramente più "sicuro"
            #for a in self.__accounts:
            #    a.SyncListGroups.toRemove.append(group.syncTag)
            group :Group
            for group in groupsToDelete[syncTag]:
                group.account.SyncListGroups.toRemove.append(group.syncTag)


        #-------------------------
        #--- gruppo aggiornato ---
        #-------------------------

        lastExecution=self.__configurations.getLastExecution()
        for syncTag in commonGroups:

            if len(commonGroups[syncTag])!= numAccounts:    #escludo quelli da "cancellare" ( già fatti prima )
                continue
            tmp = [ g for g in commonGroups[syncTag] if g.updateTime > lastExecution  ] #prendo tutti quelli che sono stati modificati dopo l'ultima esecuzione
            if len(tmp)==0:
                continue        

            toUpdate+=1
            #prendo il pià recente
            master:Group = sorted(commonGroups[syncTag], key=lambda x: x.updateTime,reverse=True)[0]
          
            #prendo gli altri account a cui applicare l'update
            #otherAccounts=self.getOtherAccounts(master.account)
            #for account in otherAccounts:
            #    account.getGroupBySyncTag(master.syncTag).copyFrom(master)      

            #metodo sopra fa più passaggi, questo dovrebbe essere la stessa cosa
            
            g:Group
            for g in commonGroups[syncTag]:
                if g!=master:           #aggiorno tutti tranne il master
                    tmp = g.clone()
                    tmp.copyFrom(master)
                    g.account.SyncListGroups.toUpdate.append(tmp)

                
            
        #--------------------
        #--- nuovo gruppo ---
        #--------------------

        #lo faccio dopo l'update e cancellazione, altrimenti appena gli do un syncTag e mi sballa i controlli precedenti

        #per ogni account
        for account in self.__accounts:

            account:Account=account
            altriAccount = self.getOtherAccounts(account)

            #recupero i gruppi nuovi
            nuoviGruppi=[g for g in account.groups if g.syncTag==None]
            for nuovoGruppo in nuoviGruppi:
                toAdd+=1
                #a ciascuno do un sync tag
                nuovoGruppo.syncTag=self.newSyncTag()

                oldName=nuovoGruppo.name
                i=1
                #controllo se il nome del nuovo gruppo non è duplicato in qualche altro account
                while len([a for a in altriAccount if a.getGroupByName(nuovoGruppo.name)]) > 0:
                    nuovoGruppo.name = oldName+" - collision "+str(i)
                    i+=1


                # e li imposto da creare
                account.SyncListGroups.toUpdate.append(nuovoGruppo)
                for altroAccount in altriAccount: 
                    altroAccount:Account=altroAccount
                    altroAccount.SyncListGroups.toAdd.append(nuovoGruppo.cloneBody())
        

        log("identificati:")
        log.addIndentation(1)
        log("nuovi: ",toAdd )
        log("aggiornati: ",toUpdate )
        log("rimossi: ",toDelete )
        log.addIndentation(-1)



        log("invio dati a Google...")
        log.addIndentation(1)
        for account in self.__accounts:
            log(account.user,":")
            log.addIndentation(1)
            log("sincronizzazione in corso...")
            log.addIndentation(1)

            account.applySyncListGroups()

            log.addIndentation(-1)
            log.addIndentation(-1)

        log.addIndentation(-1)



    def syncContacts(self):
        log("identifico i contatti da syncronizzare...")
        toDelete=0
        toUpdate=0
        toAdd=0


        #recupero tutti gli che hanno un sync e li metto in "comune"
        commonContacts={}
        account:Account
        for account in self.__accounts: 
            for c in account.contacts:
                if c.syncTag!=None:
                    if not c.syncTag in commonContacts:
                        commonContacts[c.syncTag]=[]
                    commonContacts[c.syncTag].append(c)

            
        #---------------------------
        #--- contatto cancellato ---
        #---------------------------

        #cerco tutti quei gruppi che non li trovo "N" volte all'interno di ogni vettore di syncTag 
        #( se un utente cancella un gruppo, dovrei vedere che non tutti gli account hanno quel determinato gruppo)
        numAccounts=len(self.__accounts)

        contactsToDelete= { syncTag:commonContacts[syncTag] for syncTag in commonContacts if len(commonContacts[syncTag])<numAccounts }
        toDelete = len(contactsToDelete)

        for syncTag in contactsToDelete:
            
            #dovrebbe essere meno ottimizzato ma sicuramente più "sicuro"
            #for a in self.__accounts:
            #    a.SyncListContacts.toRemove.append(contact.syncTag)
            contact :Contact
            for contact in contactsToDelete[syncTag]:
                contact.account.SyncListContacts.toRemove.append(contact.syncTag)

        
        #---------------------------
        #--- contatto aggiornato ---
        #---------------------------

        lastExecution=self.__configurations.getLastExecution()
        for syncTag in commonContacts:

            if len(commonContacts[syncTag])!= numAccounts:    #escludo quelli da "cancellare" ( già fatti prima )
                continue
            tmp = [ c for c in commonContacts[syncTag] if c.updateTime > lastExecution  ] #prendo tutti quelli che sono stati modificati dopo l'ultima esecuzione
            if len(tmp)==0:
                continue        

            toUpdate+=1
            #prendo il più recente
            master:Contact = sorted(commonContacts[syncTag], key=lambda x: x.updateTime,reverse=True)[0]
          
            #prendo gli altri account a cui applicare l'update
            #otherAccounts=self.getOtherAccounts(master.account)
            #for account in otherAccounts:
            #    account.getGroupBySyncTag(master.syncTag).copyFrom(master)      

            #metodo sopra fa più passaggi, questo dovrebbe essere la stessa cosa
            
            c:Contact
            for c in commonContacts[syncTag]:
                if c!=master:           #aggiorno tutti tranne il master
                    c.copyFrom(master)
                    c.copyMembership(master)
                    c.account.SyncListContacts.toUpdate.append(c)

                
            
        #----------------------
        #--- nuovo contatto ---
        #----------------------

        #lo faccio dopo l'update e cancellazione, altrimenti appena gli do un syncTag e mi sballa i controlli precedenti

        #per ogni account
        account:Account
        for account in self.__accounts:
            altriAccount = self.getOtherAccounts(account)

            #recupero i contatti nuovi
            nuoviContatti=[c for c in account.contacts if c.syncTag==None]
            for nuovoContatto in nuoviContatti:
                toAdd+=1
                #a ciascuno do un sync tag
                nuovoContatto.syncTag=self.newSyncTag()
                

                # e li imposto da creare
                account.SyncListContacts.toUpdate.append(nuovoContatto)
                altroAccount:Account
                for altroAccount in altriAccount: 
                    #creo un Contact temporano con il body del nuovo contatto
                    tmp=Contact.fromGoogleObj(nuovoContatto.cloneBody(),altroAccount)
                    #inserisco il contatto nei gruppi corretti
                    tmp.copyMembership(nuovoContatto)
                    #aggiungo un clone del body alla lista di contatti da aggiungere a quell'account
                    altroAccount.SyncListContacts.toAdd.append(tmp.cloneBody())
        



        
        log("identificati:")
        log.addIndentation(1)
        log("nuovi: ",toAdd )
        log("aggiornati: ",toUpdate )
        log("rimossi: ",toDelete )
        log.addIndentation(-1)



        log("invio dati a Google...")
        log.addIndentation(1)
        for account in self.__accounts:
            log(account.user,":")
            log.addIndentation(1)
            log("sincronizzazione in corso...")
            log.addIndentation(1)

            account.applySyncListContacts()

            log.addIndentation(-1)
            log.addIndentation(-1)
        log.addIndentation(-1)


            
       
    def force_syncPhotos(self):
        """controlla per ogni contatto le foto se sono sincronizzate, OPERAZIONE LUNGA"""
        if len(self.accounts)<2:        #non dovrebbe mai succedere...
            return
        
        log("creazione lista contatti")
        allContacts={}
        account:Account
        for account in self.accounts:
            for contact in account.contacts:
                if not contact.syncTag in allContacts:
                    allContacts[contact.syncTag]=[]
                allContacts[contact.syncTag].append(contact)

        log("syncronizzazione foto: ")
        log.addIndentation(1)
        lastExectuion=self.__configurations.getLastExecution()
        for syncTag in allContacts:
            contactsSorted = sorted(allContacts[syncTag], key=lambda x: (x.updateTime),reverse=True)
            #il primo è il più recente
            master:Contact=contactsSorted[0]

            #se la modifica è stata fatta dopo l'ultima esecuzione 
            if(master.updateTime > lastExectuion):
                
                log(master.name ," (",master.account.user,")-> ",master.photo)
                if master.photo:            #se la foto c'è -> settala
                    
                    #google usa un metodo suo per definire la dimensione della foto da visualizzare ( non è un parametro )
                    #alla fine dell'url c'è un = con "S" e la dimensione.
                    #mettendo un numero molto più grande della dimensione viene ritornata l'immagine a dimensione reale
                    #tolgo quindi qualsiasi cosa che c'è dopo l'uguale e ci metto "s10000"
                    equal_position = master.photo.find("=")
                    assert equal_position != -1,"= non trovato, nuova struttura dell'url di google?? "+master.photo
                    urlFullSize = master.photo[:equal_position + 1]+"s10000"

                                        
                    response = requests.get(urlFullSize)       #prendo la foto a dimensione "grande" TODO: parso l'url e modifico il parametro in corretto
                    image_bytes = bytearray(response.content)       #recupero l'array di byte

                    otherContact = contactsSorted[1:]               #prendo tutti gli altri contatti associati
                    contact:Contact
                    log.addIndentation(1)
                    for contact in otherContact:     
                        log(contact.account.user)
                        contact.updatePhoto(image_bytes)            #gli setto l'immagine
                    log.addIndentation(-1)

                else:
                    otherContact = contactsSorted[1:]               #prendo tutti gli altri contatti associati
                    contact:Contact
                    log.addIndentation(1)
                    for contact in otherContact: 
                        if contact.photo!=None:
                            log(contact.account.user)       
                            contact.deletePhoto()            #cancello l'immagine
                    log.addIndentation(-1)

        log.addIndentation(-1)
    

        

        



    def deSync(self):
        """rimuove tutti i syncTag da tutti i contatti e gruppi"""
        a:Account
        for a in self.accounts:
            for g in a.groups:
                g.syncTag=None
                a.SyncListGroups.toUpdate.append(g)

        for a in self.accounts:
            for c in a.contacts:
                c.syncTag=None
                a.SyncListContacts.toUpdate.append(c)


        for a in self.accounts:
            a.applySyncListGroups()
            a.applySyncListContacts()


    def newSyncTag(self):
        """Return a new unique sync tag"""
        le = string.ascii_lowercase

        while True:
            newSyncTag_ = "".join(random.choices(le, k=20))
            if not self.syncTagExist(newSyncTag_) and not newSyncTag_ in self.__temporaryReservedSyncTag :
                self.__temporaryReservedSyncTag.append(newSyncTag_)
                return newSyncTag_
            
        
    @property
    def accounts(self):
        return [*self.__accounts]