#recupero il path del file corrente, prendo la cartella padre e la aggiunto al sys.path ( variabili di sistema del processo )
#cosi trova le librerie della cartella Libs

import pathlib
from ConfigManager import ConfigManager


from Google.Account import Account
from Google.Contact import Contact
from Google.Group import Group
from Google.SyncManager import SyncManager

import os

from Utils.Logger import log
import argparse


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
    p.add_argument("-f", "--file", action="store_true", help="Save output to file")
    return p.parse_args()



def main():
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


    log("ultima esecuzione ",configurations.getLastExecution())


    #download contacts e gruppi
    log("scarico i dati... ")
    log.addIndentation(1)
    syncManager = SyncManager(configurations)
    for mail in configurations.getMails():
        log(mail,"...")
        syncManager.addAccount(Account(configurations.getAPI_JSON_path(), mail))
    log.addIndentation(-1)
    log("dati scaricati!")

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
        


    configurations.save()
    


if __name__ == "__main__":
    main()










