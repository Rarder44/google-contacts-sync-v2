from ConfigManager import ConfigManager
from Google.Account import Account
from Google.Contact import Contact
from Google.SyncManager import SyncManager
import pathlib
import os
import json
import datetime,pytz
import shutil
class BackupManager:
    #TODO: LOG!!

    def __init__(self, syncManager:SyncManager,configManager:ConfigManager):
        self.syncManager=syncManager
        self.configManager=configManager
        self.backupFolder="backups"



    def backup(self,ignoreHistory=False):
        
        #TODO: se ci sono problemi di "performance"
        # ( visto che tutto l'oggetto viene caricato in memoria ram e potebbe pesare tanto con anche le immagini )
        # potrebbe essere necessario salvare le immagini individualmente con un "numero"/ID, e salvare nel json solo il numero

        if len(self.syncManager.accounts)==0:
            return
        
        numBackup = int(self.configManager.data["DEFAULT"]["backup_history"])
        if numBackup==0 and ignoreHistory==False:
            return  #è stato lanciato un backup ma la configurazione non lo permette!
        
        time= datetime.datetime.now().strftime("%Y-%m-%d %H_%M_%S.%f")
        p=f"{self.backupFolder}/{time}/backup.json"
        path= pathlib.Path(p)


        if not os.path.exists(path.parent):
            os.makedirs(path.parent)

        jsonOut= self.syncManager.accounts[0].exportJSON(True)
        f = open(path, "w")
        f.write(json.dumps(jsonOut))
        f.close()

        if ignoreHistory:
            return
        
        
        subfolders = [ f.path for f in os.scandir(self.backupFolder) if f.is_dir() ]
        if len(subfolders) > numBackup:
            #cancello tutte le cartelle più vecchie 
            subfolders.sort()
            subfoldersToDelete = subfolders[:(len(subfolders)-numBackup)]
            for s in subfoldersToDelete:
                shutil.rmtree(s)
            
            

    def backup_all(self):
        """crea un backup per ogni account"""
        if len(self.syncManager.accounts)==0:
            return
               
        time= datetime.datetime.now().strftime("%Y-%m-%d %H_%M_%S.%f - all")
        pathParent= pathlib.Path(f"{self.backupFolder}/{time}")


        if not os.path.exists(pathParent):
            os.makedirs(pathParent)

        a:Account
        for a in self.syncManager.accounts:
            jsonOut= a.exportJSON(True)
            f = open(pathParent/ f"{a.user}.json", "w")
            f.write(json.dumps(jsonOut))
            f.close()

    

        

    def restore(self,backupFile):

        #se passato da parametro non serve in quanto il parametro è già controllato; lo lascio cmq visto che può essere generico 
        assert os.path.isfile(backupFile),f"{backupFile} non è un file"
        
        f = open(backupFile, "r")
        obj = json.loads(f.read())
        f.close()

        #rimuovo tutto
        self.syncManager.removeAll(Security=True)

        #creo un account "temporaneo" dove carico il backup
        #lo considero il "master" più aggiornato ( forzo la data di update? )
        master = Account.fromBackup(obj)
        accounts=self.syncManager.accounts

        #copio i groups
        for g in master.groups:
            account:Account
            for account in  accounts:
                account.SyncListGroups.toAdd.append(g.cloneBody())

        for account in accounts:
            account.applySyncListGroups()


        #copio i contacts
        for c in master.contacts:
            account:Account
            for account in accounts: 
                #creo un Contact temporano con il body del nuovo contatto
                tmp=Contact.fromGoogleObj(c.cloneBody(),account)
                #inserisco il contatto nei gruppi corretti
                tmp.copyMembership(c)
                #aggiungo un clone del body alla lista di contatti da aggiungere a quell'account
                account.SyncListContacts.toAdd.append(tmp.cloneBody())

        for account in accounts:
            account.applySyncListContacts()


        #sincronizzo le immagini
        for contact in master.contacts:
            if contact.photoCache:          #prendo tutti quelli che hanno una cache ( ovvero che l'immagine era salvata nel file )
                for account in accounts:
                    cont = account.getContactBySyncTag(contact.syncTag)     #recupero il contatto dell'account tramite syncTag
                    cont.updatePhoto(contact.photoCache)                    #gli carico l'immagine
                

        
        self.configManager.save()       #aggiorno la data
        




        
        pass