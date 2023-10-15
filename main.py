#recupero il path del file corrente, prendo la cartella padre e la aggiunto al sys.path ( variabili di sistema del processo )
#cosi trova le librerie della cartella Libs

import pathlib
from BackupManager import BackupManager
from ConfigManager import ConfigManager


from Google.Account import Account
from Google.Contact import Contact
from Google.Group import Group
from Google.SyncManager import SyncManager

import os

from Utils.Logger import log
import argparse
import json
import pathlib

import Google._patcher

#creare una key di autenticazione ad un servizio 
    #vai qua -> https://console.cloud.google.com/projectselector2/iam-admin/serviceaccounts?supportedpurview=project&authuser=4
    #crea un progetto
        #dai i permessi di "People API" e "Contacts" ( o durante la creazioneo o nel menu in alto a sx -> Api e Servizi | "+ Abilita Api e Servizi")
    #crea le credenziali 
        #menu in alto a sx -> Api e Servizi
        #menu a sx -> credenziali
        #"+ Crea credenziali" -> ID client OAuth 2.0 -> "Applicazione Desktop"
        # scarica il JSON 

    #dare i permessi agli utenti di accedere all'app/progetto
        #menu in alto a sx -> Api e Servizi
        #menu a sx -> "Schermata consenso OAuth"
        #cerca la voce "Utenti di prova" e clicca su "+ Add Users"
        #inserire gli account mail da sincronizzare

        
def arguments():

    def is_valid_file(parser, arg):
        if not os.path.exists(arg):
            parser.error("The file %s does not exist!" % arg)
        else:
            return open(arg, 'r')  # return an open file handle
        

    # parse command line
    p = argparse.ArgumentParser(
        description="""
    Sync google contacts.

    For full instructions see
    https://github.com/Rarder44/google-contacts-sync-v2
        """,
        epilog="""""",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--desync", action="store_true", help="Removes the synchronization tag from groups and contacts")
    p.add_argument("--file", action="store_true", help="Save output to file")
    p.add_argument("--only_backup", action="store_true", help="Read only operation, read all accounts and create a backup for each")
    p.add_argument("--restore", dest="restore_filename", required=False,help="Backup file path to be applied", metavar="BACKUP_FILE_PATH",type=lambda x: is_valid_file(p, x))
    return p.parse_args()



def main():
    Google._patcher.patch()

    configFile="config.ini"

    args=arguments()
    if args.file:
        log.filename="LOG.txt"

    

    #carico la configurazione
    log("carico la configurazione da ",configFile)
    confDir= pathlib.Path("configs")
    os.makedirs(confDir, mode=0o755, exist_ok=True)
    confFile = confDir / configFile
    configurations = ConfigManager(confFile)
    if not configurations.isLoaded:
        exit()
    syncManager = SyncManager(configurations)
    backupManager = BackupManager(syncManager,configurations)
    


    log("ultima esecuzione ",configurations.getLastExecution())

    #download contacts e gruppi
    log("scarico i dati... ")
    log.addIndentation(1)
    
    for mail in configurations.getMails():
        log(mail,"...")
        syncManager.addAccount(Account(configurations.getAPI_JSON_path(), mail))
    log.addIndentation(-1)
    log("dati scaricati!")

    #controllo se devo solo fare il backup
    if args.only_backup:
        log("inizio backup...")
        backupManager.backup_all()
        log("backup completato")
        return
    
    #controllo se devo ripristinare
    if args.restore_filename!=None:
        backupManager.restore(args.restore_filename.name)
        return
    

    #controllo se devo solo desincronizzare
    if args.desync:
        log("deSync: rimozione dei tag da gruppi e contatti...")
        syncManager.deSync()
        log("deSync: done!")
        exit()

    #TEST:DEBUG - crea 1000 contatti casuali dentro il primo account
    #for i in range(1000):
    #    body = {"names": [{"givenName": f"test-{i}"}]}
    #    syncManager.accounts[0].SyncListContacts.toAdd.append(body)
    #
    #syncManager.accounts[0].batchCreateContacts()



    #inizio sync gruppi
    log("inizio sincronizzazione gruppi...")
    log.addIndentation(1)

    syncManager.syncGroups()

    log.addIndentation(-1)
    log("fine sincronizzazione gruppi")


    #inizio sync contatti
    log("inizio sincronizzazione contatti...")
    log.addIndentation(1)

    syncManager.syncContacts()

    log.addIndentation(-1)
    log("fine sincronizzazione gruppi")

    if configurations.data["DEFAULT"]["photo_sync"]:
        log("inizio sincronizzazione foto...")
        log.addIndentation(1)

        syncManager.force_syncPhotos()

        log.addIndentation(-1)
        log("fine sincronizzazione foto")
        
    if  int(configurations.data["DEFAULT"]["backup_history"])>0:
        log("inizio backup...")
        backupManager.backup()
        log("backup completato")
   
    configurations.save()
    


if __name__ == "__main__":
    main()










