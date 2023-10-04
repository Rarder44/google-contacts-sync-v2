#classe che mi permette di loggare in maniera semplice e colorata
import datetime
import os

class Logger:
    #tutto ciò che c'è qua viene eseguito una volta sola all'inizializzazione della classe
    os.system('color')          #permette di abilitare i colori ( e caratteri di escape ) nel terminale cmd/powershell

    class bcolors:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        CYAN = '\033[96m'
        GREEN = '\033[92m'
        WARNING = '\033[93m'
        YELLOW = '\033[93m'
        FAIL = '\033[91m'
        RED = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'
        UNDERLINE = '\033[4m'

    def __init__(self) -> None:
        self.filename: str | None = None
        self.__indentation=0
        


 
    def addIndentation(self,n=1):
        """Fornire un numero negativo per ridurre l'indentazione"""
        self.__indentation+=n
        if self.__indentation<0:
            self.__indentation=0


    def __call__(self,*values,**vargs):
        
        valuesWithIndentation = Logger.__add_indentation(*values,indentation=self.__indentation)
        valuesWithIndentation=("     ",)+valuesWithIndentation
        self.__print(*valuesWithIndentation,**vargs)



    def err(self,*values):
        valuesWithIndentation = Logger.__add_indentation(*values,indentation=self.__indentation)
        valuesWithIndentation=("[ERR]",)+valuesWithIndentation
        self.__print(*valuesWithIndentation,color=Logger.bcolors.RED)

    def war(self,*values):
        valuesWithIndentation = Logger.__add_indentation(*values,indentation=self.__indentation)
        valuesWithIndentation=("[WAR]",)+valuesWithIndentation
        self.__print(*valuesWithIndentation,color=Logger.bcolors.YELLOW)


    def __print(self, *values,**vargs):
        
        v= Logger.__clean_vargs_for_print(**vargs)

        if "color" in vargs:
            #non posso fare una stampa unica se no mi mette uno spazio in più 
            #quindi
            #stampo l'inizio del colore ( non andando a capo)
            print(vargs["color"],end='')
            
            #stampo il contenuto del messaggio ( non andando a capo ma rispettando gli altri parametri)
            tmp ={**v}
            tmp["end"]=''
            print(*values,**tmp)

            #stampo il resto del messaggio rispettando tutti i parametri
            print(Logger.bcolors.ENDC, **v)
        else:
            print(*values, **v)

        if self.filename:
            vargs["filename"]=self.filename
            Logger.__writeToFile(*values,**vargs)     

    def __writeToFile(*values,**vargs):
        """accetta come vargs\n
                sep -> separator \n
                end -> carattere terminatore\n
                filename -> nome del file in cui salvare 
        """
        
        # highly inefficient, but even if it crashes, I can save the last instruction
        if "filename" in vargs:
            with open(vargs["filename"], "a") as f:
                vargs["flush"]=True
                vargs["file"]=f
                v = Logger.__clean_vargs_for_print(**vargs)

                values = ("[" + str(datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")) + "]",) + values
                print(*values, **v)

    def __clean_vargs_for_print(**vargs):
        valid=["sep","end","flush","file"]
        #TODO: get args / signature from print function direct

        return {key:vargs[key] for key in vargs if key in valid}
    
    def __add_indentation(*values,indentation=0):
        if indentation==0:
            return values 
        return ('     '*indentation,)+values        #non uso il tab xke si sminchia l'allineamento tra console e file
        


log = Logger()
#l.filename="TEST.txt"
#l("ciao",color=Logger.bcolors.GREEN)
#l.addIndentation(1)
#l("ciao")
#l.addIndentation(1)
#l.err("a",{"b":1,"c":[1,2,3,4]},"CIAAAAAOOOO")
#l.addIndentation(-1)
#l.war("a",{"b":1,"c":[1,2,3,4]},"CIAAAAAOOOO")
#l.addIndentation(-1)
#l.err("AAAAA")
#l.addIndentation(-1)
#l.war("BBBBB")