"""
Interface web monopage pour python, via http et websocket
"""

# pour faire tourner des serveurs
import socket
import select # select
import threading # Thread,Lock

# pour la négociation 101 Switching Protocols/Upgrade: websocket
import hashlib
import base64

# pour communiquer avec JS
import json # dumps, loads

# lancer le navigateur
import webbrowser # open

class StopInter(Exception): pass

class StopInter(Exception): pass

class Inter:
    """
    Interface par une page web, dont les éléments sont manipulables et consultables 
    depuis python, à qui elle envoie tous ses événements clavier et souris.
    """
    _ws_port = 5056
    _chemin_js = "/js"
    _js = """let socket = new WebSocket("ws://127.0.0.1:_ws_port");
let readySent = true;
let waiting = [];

socket.onopen = function(e) {
  console.log("[open] Connection established");
  if (readySent == false)
  {
      transmettre("ready", [window.innerWidth, window.innerHeight]);
  }
  for (let i = 0; i < waiting.length; i++)
  {
      transmettre(waiting[i][0], waiting[0][1]);
  }
};

socket.onmessage = function(event) {
    faire(JSON.parse(event.data));
};

socket.onclose = function(event) {
  if (event.wasClean) {
    console.log(`[close] Connection closed cleanly, code=${event.code} reason=${event.reason}`);
  } else {
    console.log('[close] Connection died');
  }
};

socket.onerror = function(error) {
  console.log(`[error]`);
};        

function envoi(obj) {
  let code=undefined;
  if (obj != undefined) 
      code = JSON.stringify(obj)
  if (code != undefined)
    socket.send(code); 
  else
      console.log("nothing to send");
};

function transmettre(act,obj) {
    if (obj==undefined) obj="";
    if (socket.readyState != 1)
    {
        waiting.push([act,obj]);
        return;
    }
    socket.send(JSON.stringify([act,obj]));
};

document.addEventListener("DOMContentLoaded", (event) => {
    document.getElementsByTagName('BODY')[0].id="body"; 
    document.getElementsByTagName('HEAD')[0].id="head"; 
    document.body.oncontextmenu=(e)=>{return false;};
    if (socket.readyState == 1) {
        transmettre("ready", [window.innerWidth, window.innerHeight]);
    }
    else {
        readySent = false;
    }
});

function sendWindowResize() {
    transmettre("get_window_size", [window.innerWidth, window.innerHeight]);
}

window.addEventListener("resize", sendWindowResize);

function faire(o){
    for (dico of o)
    {
        if (dico["type"] == undefined)
        {
            continue;
        }
        
        let elem = document.getElementById(dico["id"]);
        let data = dico["data"];
        let type = dico["type"];
        
        if (elem == null)
        {
            if (type == "create" && (dico["tagName"] != undefined))
            {
                elem = document.createElement(dico["tagName"]);
                for (attr in data)
                {
                    elem[attr]=data[attr];
                }
                let parent = document.getElementById(dico["parent_id"]);
                if ((parent == null) || (parent == undefined))
                {
                    parent = document.body;
                }
                if (parent != null)
                {
                    parent.appendChild(elem);
                }
            }
            else {
                console.log("No such element with this identifier exists, id:", dico["id"]);
            }
            continue;
        }
        
        if (type == "draw")
        {
            var context = elem.getContext("2d");
            context.imageSmoothingEnabled = false;
            var img = new Image;
            img.src = data["i"];
            img.onload = function(){
                if (data["c"]) {
                    context.clearRect(data["x"], data["y"], data["s"], data["s"]);
                }
                context.drawImage(img, data["x"], data["y"], data["s"], data["s"]);
            };
        }
        else if (type == "clear")
        {
            var context = elem.getContext("2d");
            context.clearRect(data["x"], data["y"], data["w"], data["h"]);
        }
        else if (type == "delete")
        {
            elem.parentNode.removeChild(elem);
        }
        else if (type == "children")
        {
            while (elem.firstChild){
                elem.removeChild(elem.lastChild);
            }
        }
        else if (type == "content")
        {
            elem.innerText = data;
        }
        else if (type == "class-a")
        {
            elem.classList.add(data);
        }
        else if (type == "class-t")
        {
            elem.classList.add(data["c"]);
            setTimeout(function(){elem.classList.remove(data["c"]);},data["t"]);
        }
        else if (type == "class-r")
        {
            elem.classList.remove(data);
        }
        else if (type == "attributes")
        {
            for (attr in data)
            {
                elem[attr]=data[attr];
            }
        }
        else if (type == "style")
        {
            for (sattr in data["style"])
            {
                elem.style[sattr] = data["style"][sattr]; 
            }
        }
        else {
            console.log("Couldn't handle the request. Type: " + type);
        }
    }
};

const ueh = (event) => {
  event.preventDefault();
  event.returnValue = true;
};

"""

    def __init__(self,page:str=None):
        """
        Initialise une instance de Inter
        
        Paramètres :
          - page : URL de la page d'interface à charger un démarrage.
            Le chemin est relatif, donné à partir du dossier d'exécution du script.
        
        Valeur renvoyée : self
        
        Lorsqu'aucune page n'est indiquée en paramètre, l'interface est générée automatiquement par le serveur,
        c'est une page vide à la racine du site.
        
        Lorsqu'une page est indiquée, elle peut être interceptée par un générateur défini par la méthode reponse_http.
        Sinon, le fichier est cherché sur le disque dur.
        
        Dans les deux cas, le code javascript nécessaire à l'interface est automatiquement injecté juste avant
        la balise </head>, qui doit être écrite en minuscules.
        """
        
        self._verrou_ws = threading.Lock()
        
        # port ws
        Inter._ws_port += 1
        self._ws_port = Inter._ws_port

        self.liste_connect = [] # liste des sockets à suivre
        self.wss_on = True      # drapeau de la boucle du serveur wss
        self.ws_actif = None    # dernier socket ws ouvert

        self.ready: bool = False
        self.pending: list[str] = []

        self._continuer = True # passe à False pour quitter le serveur une fois que toutes les donnés du socket ont été purgées

        self._handlers = {  "_mh": ((lambda s,d: None),False), 
                            "_kh":((lambda s,d: None),False),
                            "_skh":((lambda k: None),False)}

        self._touches = {}

        self._htresponse = {}

        self.reponse_http(Inter._chemin_js, lambda c,p: (Inter._js.replace("_ws_port",str(self._ws_port),1),"js"))

        self._threads_fils=[]

        self._page_dem=page

        self._dem_page_loaded = False

        self._stop_handler = lambda : print("Extinction.")

        self._stopped=False

        self.window_width = -1
        self.window_height = -1
        self.window_size_changed = False

    def touches(self):
        """
        Renvoie un dictionnaire dont l'ensemble des clés est l'ensemble des touches actuellement pressées.
        Paramètres : aucun.
        
        Valeur renvoyée : un dicitonnaire dont les clés sont les KeyCode des touches actuellement pressées.
        
        Pré-requis : avec initialisé le clavier et mis en place un gestionnaire simple avec Inter().gcs
        
        La valeur associée à une clé de ce dictionnaire est la liste transmise par l'interface, celle qui
        est passée en paramètre p au gestionnaire défini par la méthode gestionnaire_clavier.
        """
        return self._touches

    def gestionnaire(self, message:str,handler:callable,nonbloc:bool=False):
        """
        Associe un gestionnaire à un message
        Paramètres :
          - message : le message à intercepter
          - handler : fonction à deux paramètres à lancer à l'interception
          - nonbloc : booléen indiquant si le gestionnaire est synchrone (False) ou asynchrone (True)

        Valeur renvoyée : None

        Après le démarrage de l'interface, tous les appels javacript de transmission sont interceptés.
        Lorsque l'on intercepte transmission(m,o) avec m=message, l'interface déclenchent un appel de
        handler(m,o)
        """
        self._handlers[message] = (handler, nonbloc)

    def gss(self, handler:callable):
        """
        Définit un gestionnaire de souris simple
        Paramètres :
          - handler : fonction à trois paramètres appelée lors d'une pression sur un bouton de la souris

        Valeur renvoyée : None

        Les pararmètres passés à handler sont
          - objet   : l'id de l'objet qui a reçu le clic
          - x       : abscisse dans l'objet du pointeur au moment du clic, en pixel
          - y       : ordonnée dans l'objet du pointeur au moment du clic, en pixel        
        """
        self._handlers["_mh"] = ((lambda e,p: handler(p[0],p[2],p[3]) if e=="D" else None),True)

    def _kh(self,e,p):
        """
        handler clavier pour gcs : 
         - filtre les "U" 
         - gère Inter()._touches
         - effectue l'appel bloquant ou non du handler simple
        """
        touches = self._touches

        if e=="D":
            touches[p[5]]=p
            key=p[4]
        if e=="U":
            if p[5] in touches:
                del touches[p[5]]
            key=''

        handler,nonbloc = self._handlers["_skh"]
        if nonbloc:
            handler_thread = threading.Thread(target=lambda : handler(key))
            self._threads_fils.append(handler_thread)
            handler_thread.start()
        else:
            handler(key)

    def gcs(self, handler:callable=lambda _: None,nonbloc:bool=True):
        """
        Définit un gestionnaire de clavier simple
        Paramètres :
          - handler : fonction à un paramètre appelée lors d'une pression sur une touche

        Valeur renvoyée : None

        Le pararmètres passé à handler est une chaîne qui indique la touche pressée.

        En cas de pressions multiples, on peut obtenir l'ensemble des KeyCode des touches 
        actuellement pressées comme l'ensemble des clés du dictionnaire renvoyé par
        la méthode touches()
        
        Lorsque gcs est appelée sans paramètre, seul le dictionnaire touches() est géré.
        """
        self._handlers["_kh"] = (self._kh,False)
        self._handlers["_skh"] = (handler,nonbloc)

    def gestionnaire_souris(self, handler:callable,nonbloc:bool=False):
        """
        Définit le gestionnaire de la souris
        Paramètres :
          - handler : fonction à deux paramètres appelée lors d'un événement de la souris

        Valeur renvoyée : None

        Pour chaque clic, deux événements ont lieu :
          - un appel handler("D",p) lorsqu'un bouton est pressé
          - un appel handler("U",p) lorsqu'un bouton est relâché.
          
        Le paramètre p passé à handler est la liste [target.id,buttons,layerX,layerY]
          - target.id : attribut id de l'objet qui a reçu le clic
          - buttons   : entier qui indique quels boutons sont pressés
          - layerX,layerY : coordonnées, en pixels, relativement au coin supérieur gauche de la page
          
        Le recours à cette méthode est inutile si l'on gère la souris avec gss.
        """
        self._handlers["_mh"] = (handler,False)

    def gestionnaire_clavier(self, handler:callable):
        """
        Définit le gestionnaire de clavier
        Paramètres :
          - handler : fonction à deux paramètres appelée lors d'un événement du clavier
          
        Valeur renvoyée : None

        Pour chaque touche pressée, deux événements ont lieu :
          - un appel handler("D",p) lorsqu'une touche est pressée
          - un appel handler("U",p) lorsqu'une touche est relâchée.
          
        Le paramètre p passé à handler est la liste [altKey,ctrlKey,shiftKey,metaKey,key,code,repeat,timeStamp]
          - altKey,ctrlKey,shiftKey,metaKey : booléens indiquant si Alt, Control, Shift et Meta sont pressées
          - key : chaine de caractères représentant la saisie de caractère effectuée
          - code : chaine de caractères représentant la touche pressée sur un clavier standard Qwerty
          - repreat : booléen indiquant si la touche est en train d'être maintenue
          - timeStamp : entier donnant la chronologie des événements
          
        Le recours à cette méthode est inutile si l'on gère le clavier avec gcs.
        """
        self._handlers["_kh"] = (handler,False)

    def init_souris(self):
        """
        Configure l'interface pour intercepter les événements de la souris.
        
        À exécuter avant la mise en place d'un gestionnaire de souris avec 
        gestionnaire_souris ou gss.
        
        Effectué par défaut au démarrage de l'interface.
        """
        if self.ws_actif is None:
            raise Exception("WS inactif")

        self.injecte("""
  window.addEventListener("mousedown", (e) => { 
    transmettre('**MD**',[e.target.id,e.buttons,e.layerX,e.layerY]);
  });
  window.addEventListener("mouseup", (e) => {
    transmettre('**MU**',[e.target.id,e.buttons,e.layerX,e.layerY]);    
  });
        """)

    def init_clavier(self):
        """
        Configure l'interface pour intercepter les événements du clavier.
        
        Action à affectuer avant la mise en place d'un gestionnaire de clavier
        avec gestionnaire_clavier ou gcs.
        
        Cette initialisation n'est pas effectuée par défaut au démarrage 
        de l'interface.
        """
        if self.ws_actif is None:
            raise Exception("WS inactif")

#        self._touches={}

        self.injecte("""
  document.body.addEventListener("keyup", (e) =>{
    transmettre('**KU**',[e.altKey,e.ctrlKey,e.shiftKey,e.metaKey,e.key,e.code,e.repeat,e.timeStamp]); 
  });
        """)
        self.injecte("""
  document.body.addEventListener("keydown", (e) => {
    transmettre('**KD**',[e.altKey,e.ctrlKey,e.shiftKey,e.metaKey,e.key,e.code,e.repeat,e.timeStamp]);
  });
        """)

    def demarre(self, clavier:bool=False, souris:bool=True):
        """
        Lancer l'interface.
        Paramètres :
          - clavier : booléen faisant lancer ou non la méthode init_clavier au démarrage
          - souris  : booléen faisant lancer ou non la méthode init_souris au démarrage
          
        Valeur renvoyée : None

        La méthode attend la connexion de la page web d'interface à la boucle websocket,
        puis rend la main au programme principal qui peut agir sur la page affichée par
        le navigateur et définir les gestionnaires d'événement.
        
        Suivant les événements définis, il est possible de les faire s'exécuter dans la
        boucle du serveur websocket, ou bien dans les thread séparés.
        """
                
        if self._page_dem is None:
            self.reponse_http("/", lambda c,p: ("""<!doctype html>\n<html lang="fr">\n    <head>\n        <title>wsinter</title>\n    </head>\n    <body>\n    </body>\n</html>\n""","html"))
            self._page_dem=""

        self.wss_instance = threading.Thread(target=self.wss)
        self.http_instance = threading.Thread(target=self.servir)
        self.wss_instance.start()
        self.http_instance.start()

        # on attend la connexion de la page au serveur ws
        self._verrou_ws.acquire()
        self._verrou_ws.release()

        self.injecte("window.addEventListener('beforeunload', ueh);")

        self.injecte("""window.addEventListener("unload", (e) => {transmettre('**STOP**',null);});""")

        self.gestionnaire("**STOP**",lambda m,p: self.stop(), False)

        if clavier: self.init_clavier()
        if souris:  self.init_souris()

        self.gestionnaire("ready", self._ready)

        # Taille de la fenetre en temps reel
        self.gestionnaire("get_window_size", self._set_window_size)
        self.injecte("transmettre('get_window_size', [window.innerWidth, window.innerHeight]);")

    def _ready(self, _m, o):
        self.ready = True
        for pending in self.pending:
            self._envoi(pending)
        del self._handlers["ready"]
        self._set_window_size(_m, o)

    def _set_window_size(self, _, size: list[int, int]):
        """
        Actualise la taille de la page Web pour le serveur

        Ne prend pas effet sur l'affichage dans le navigateur

        Utilise seulement par le gestionnaire d'evenement lors d'un appel par le client
        """
        self.window_width = size[0]
        self.window_height = size[1]
        self.window_size_changed = True

    def get_window_size(self):
        return (self.window_width, self.window_height)
    
    def get_window_size_if_changed(self):
        if self.window_size_changed:
            self.window_size_changed = False
            return self.get_window_size()
        else:
            return None

    def gestionnaire_stop(self, handler:callable=lambda : print("Extinction.")):
        """
        Définit le gestionnaire prenant en charge la fermeture du programme.
        Paramètres : gestionnaire à utiliser
        
        Valeur renvoyée : None
        
        La fonction passée en paramètre est appelée par la méthode stop() après l'extionction des thread
        fils et l'arrêt des boucles des serveurs http et websocket.
        
        Le programme principal ne reçoit a priori aucune indication à propos de l'extinction de l'interface.

        Pour interrompre une boucle du programme principale, le gestionnaire peut provoquer l'exception
        KeyboardInterrupt, mais peut également passer un message ad hoc par un autre moyen.
        """
        self._stop_handler = handler
        

    def stop(self):
        """
        Éteindre les serveurs, attendre les threads et quitter
          
        Valeur renvoyée : None

        La méthode stop exécute sans paramètres la fonction définie par la méthode
        gestionnaire_stop

        La méthode stop affiche un message dans l'interface, indiquant que python
        s'arrête.
        
        La méthode stop est exécutée lorsque la fenêtre du navigateur est fermée: il
        est ainsi possible d'utiliser d'utiliser gestionnaire_stop pour effectuer des
        actions spécifiques à la fermeture du programme, comme des sauvegardes.
        """

        self.injecte("window.removeEventListener('beforeunload',ueh);")
        self.injecte("alert('Python arrêté.');")

        self.wss_on = False
        self._continuer = False
        for h in self._threads_fils:
            try:
                h.join(1)
            except RuntimeError:
                pass # quand on stop() l'interface depuis un événement souris asynchrone

            if h.is_alive():
                print("Gestionnaire toujours actif...")

        if not self._continuer: self.http_instance.join()

        try:
            if not self.wss_on: self.wss_instance.join()
        except RuntimeError:

            self._stopped=True

            raise StopInter

        self._stopped=True

        self._stop_handler()

    def reponse_http(self,req:str,gen:callable):
        """
        Paramètres:
          - req : une chaine de caractères donnant un nom de ressource
          - gen : une fonction à deux paramètres, renvoyant un tuple de deux str
          
        Valeur renvoyée : None

        Le nom de la ressource est un chemin absolu depuis la racine du serveur.
        Il commence par /

        Par défaut, le serveur http cherche la ressource sur le disque dur, et envoie le document trouvé.
        Il s'agit ici de court-circuiter ce fonctionnement pour générer dynamiquement une réponse.
        
        La fonction gen est associée à la ressource req de la façon suivante:
        quand le serveur http reçoit une requête de la forme "localhost/req?param_1=va_l1&param_2=val_2&...",
        il appelle gen(req,d), où d est le dictionnaire {param_k:val_k}

        Cette fonction renvoie un tuple (extension, contenu), par exemple
        ( "html", `"`"`"<!doctype html>\n<html lang="fr"><head><title>Réponse</title></head><body>Rien...</body></html>`"`"`")
        
        Le contenu est envoyé à l'interface, comme réponse à la requête.
        
        Extensions reconnues
          - associées à un contenu de type bytes : png, jpg, jpeg, gif, ico
          - associées à un contenu de type str : htm, html, css, js, csv, json, svg, html, xml
        """ 
        self._htresponse[req]=gen

    def servir(self,ip : str = '127.0.0.1', port : int = 5080, max_conn : int = -1) -> None:
        """
        Démarre la partie serveur http de l'interface.
        
        Lors d'une utilisation standard, cette méthode n'est pas appelée par l'utilisateur.
        """
        
        def pourcent_dec_get( burl : bytes) -> str:
            """
            pratique un url->utf-8, mais =, & et % restent %-encodés, et «+» n'est pas changé en « »
            """
            res = b''
            k=0
            while k < len(burl):
                if burl[k] == b'%'[0]:
                    if int(burl[k+1:k+3],16) in [0x3D, 0x26, 0x25]:
                        #c'est '&' ou '=' ou '%', on le garde pour la fin
                        res = res + burl[k:k+3]
                    else:
                         #on décode, sauf 3D et 26 et 25
                        res = res + bytes([int(burl[k+1:k+3],16)])
                    k = k+3
                #elif burl[k] == b'+'[0]:
                #    res = res + ' '
                else:
                    res = res + bytes([burl[k]])
                    k = k + 1
            return (str(res,"utf-8"))

        def extraire( url : str) -> dict:
            """
            renvoie un dictionnaire construit à partir des paramètres passés par url
            """
            res = {}
            lc = url.split('&')
            for aff in lc:
                if '=' in aff:
                    c,v = aff.split('=',1)
                else:
                    c = aff
                    v=''
                # on décode les «=» «&» et «%» qui étaient encore encodés
                c = c.replace("%3D","=").replace("%3d","=").replace("%26","&").replace("%25","%")
                v = v.replace("%3D","=").replace("%3d","=").replace("%26","&").replace("%25","%")
                res[c] = v

            return res

        def typemime( ext : str) -> bytes:
            """
            Renvoie le type mime associé à une extension.
            Catalogue les types mime les plus courants pour les applications visées,
            les autres contenus sont typés «application/octet-stream».
            """
            mime_b = { # contenus binaire
                'png':b'image/png',
                'jpg':b'image/jpeg',
                'jpeg':b'image/jpeg',
                'gif':b'image/gif',
                'ico':b'image/x-icon',
                'mp3':b'audio/mpeg'
            }
            mime_t = { # contenus textuels
                'htm': b'text/html',
                'html': b'text/html',
                'css': b'text/css',
                'js': b'application/javascript',
                'csv': b'text/csv',
                'json': b'application/json',
                'svg':b'image/svg+xml',
                'xhtml':b'application/xhtml+xml',
                'xml':b'application/xml'
            }
            ext = ext.lower() # on standardise l'extension
            if ext in mime_b :
                return mime_b[ext],False
            elif ext in mime_t :
                return mime_t[ext],True
            else: # extension non reconnue
                return b'application/octet-stream',False

        def empaqueter(contenu : bytes, extension : str) -> bytes:
            """
            Génère un paquet HTTP à partir de contenu dont le type est donné par extension
            """

            type_mime,textuel = typemime(extension)
            if textuel:
                encodage = b'; charset=utf-8'
                if type(contenu)==type(''): contenu = bytes(contenu, "utf-8")
            else:
                encodage = b''                            

            cookies = ""

            return b'HTTP/1.1 200 OK\r\n'+bytes(cookies,"utf-8")+b'Content-Type: '+type_mime+encodage+b'\r\nConnection: close\r\nAccess-Control-Allow-Origin: *\r\nContent-Length: ' + bytes(str(len(contenu)),"utf-8") + b'\r\n\r\n' + contenu

        def gen_fichier(comm : str) -> bytes:
            """
            génère un paquet HTTP à partir du chemin du fichier
            """
            extension = comm.split('.')[-1]
            try:
                with open(comm, "rb") as fichier:
                    contenu = fichier.read()
            except: # s'il n'existe pas (ou autre erreur !)
                return bytes('HTTP/1.1 404 Not Found\r\nContent-Type: text/plain; charset=utf-8\r\nConnection: close\r\nContent-Length:17\r\n\r\nPas trouvé !\r\n\r\n','utf-8')
            else:
#                if extension.lower() == "html" :
                if comm == "./"+self._page_dem:

                    if self._dem_page_loaded:
                        print("Rechargement de la page de démarrage...")
                    else:
                        self._dem_page_loaded = True

                    contenu = contenu.replace(b'</head>',b'<script src="'+bytes(self._chemin_js,'utf-8')+b'"></script></head>')
                return empaqueter(contenu, extension)
        
        # mise en place du socket «s» en écoute sur (ip, port)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((ip, port))
        s.listen()

        print("Démarrage du serveur http://"+ip+":"+str(port))
        
        if self._page_dem is not None: 
            print("Ouverture de la page "+self._page_dem)
            webbrowser.open("http://"+ip+":"+str(port)+"/"+self._page_dem)

        # boucle du serveur : accepte les connexions sur s et on y répond
        while (self._continuer and max_conn != 0):
            
            pret,_,_=select.select([s],[],[],0.3)
            
            if pret==[]: continue
            # on accepte la connexion
            t,(h,p) = s.accept()

            # on filtre les flux
            #t.settimeout(0.05)

            try:
                req = t.recv(2048)
            except socket.timeout:
                pass
    #            print ('Timeout !')
            except:
                pass
    #            print ('Autre...')
            else:
    #            print('succès')
                
                max_conn = min(max_conn, max (max_conn - 1 ,0))
                t.shutdown(socket.SHUT_RD)
                
                query = req.split(b'\r\n',1)[0]
                elts = query.split(b" ")
                
                if elts[0] == b'GET': 
                    url = elts[1].split(b"?",1)
                    comm = pourcent_dec_get((url[0]))
                    if comm in self._htresponse:
                        # on extrait les paramètres après ? dans l'url    
                        if len(url) == 1:
                            param = ""
                        else:
                            param = pourcent_dec_get(url[1])
                        params = extraire(param)                    
                        
                        # on génère la réponse
                        resp, ext = self._htresponse[comm](comm,params)
                        
                        non_binaire = typemime(ext)[1]
                        if non_binaire:
#                            if ext == 'html':
                            if comm == "/"+self._page_dem:
                                if self._dem_page_loaded:
                                    print("Rechargement de la page de démarrage...")
                                else:
                                    self._dem_page_loaded = True
                                resp = resp.replace('</head>','<script src="'+self._chemin_js+'"></script></head>')
                            contenu = bytes(resp,'utf-8')
                        else:
                            contenu = resp
                        paquet = empaqueter(contenu,ext)
                    else: # on cherche le fichier
                        comm = '.'+comm
                        paquet = gen_fichier(comm) # la fonction gen_fichier se charge de générer le 404 si elle ne trouve pas le fichier
                    t.sendall(paquet)

                else: # ce n'est pas une requête GET
                    t.sendall(bytes('HTTP/1.1 400 Bad Request\r\nContent-Type: text/plain; charset=utf-8\r\nConnection: close\r\nContent-Length: 26\r\n\r\nRequête mal formée !\r\n\r\n','utf-8'))

            try:
                t.shutdown(socket.SHUT_WR)
    #            print ("Bye 1")
                t.close()
    #            print ("Bye 2")
            except:
    #            print('except shutdown')
                pass

    #    s.shutdown(socket.SHUT_RDWR)
        s.close()
        print("Arrêt du serveur http")

    def wss(self,ip:str="127.0.0.1"):
        """
        Partie serveur websocket de l'interface.
        
        Lors d'une utilisation standard, cette méthode n'est pas lancée par l'utilisateur.
        """

        # on bloque le démarrage de l'interface
        self._verrou_ws.acquire()

        port = self._ws_port

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((ip, port))
        s.listen()

        print("Démarrage du serveur ws://"+ip+":"+str(port))
        print("En attente de connexion.")

        self.liste_connect.append(s)

        while self.wss_on:
            prets_pour_lecture,_,_=select.select(self.liste_connect,[],[],0.3) #0.01
            for rec in prets_pour_lecture:
                data=b''
                if rec != s:
                    while rec in select.select([rec],[],[],0.01)[0]:
                        data += rec.recv(2048)
                while len(data)>0:
#                    print(data) #
                    data_start = 2
                    if data[0]==129:
    #                    print("Text frame isolée") #
                        payload_indicator = int(data[1])
                        if payload_indicator > 127:
                            masked = True
                            data_start+=4
                            payload_data = payload_indicator - 128
                        else:
                            masked = False
                            payload_data = payload_indicator
                        if payload_data <=125:
                            payload = payload_data
                        elif payload_data == 126:
                            data_start+=2
                            payload = int(data[2])*256+int(data[3])
                        elif payload_data == 127:
                            data_start+=8
                            payload=0
                            for i in range(2,10):
                                payload = payload*256+int(data[i])
                        if masked:
                            mask = data[data_start-4:data_start]
                        else:
                            mask=b''
    #                    print("payload:",payload, "data start:",data_start) #
    #                    if masked: print('mask:',mask) #
                        data_load=data[data_start:data_start+payload] # ':' -> ':data_start+payload'
                        chaine=""
                        for i,c in enumerate(data_load):
                            chaine += chr( int(c ^ mask[i%4]))
                        data=data[data_start+payload:]
                        self._process(chaine)
                    elif data[0] == 136: # close frame
#                        print("Closing frame","Index",self.liste_connect.index(rec)) #
                        self.liste_connect.remove(rec)
                        if self.ws_actif == rec: # ?
                            self.ws_actif == None # ?
                        rec.close()
                        data=b''
                        break
                    else:
#                        print("Non text frame",data[0]) #
                        data=b''
                        break
                        
                else:
#                    print("Warning : empty frame") #
                    pass

            if s in prets_pour_lecture:
                print("Nouvelle connexion")
                t,(h,p) = s.accept()
                req = t.recv(2048)
                deb = req.find(b'Sec-WebSocket-Key: ')
                fin = req.find(b'\r\n',deb)
                key = req[deb+19:fin]
                key2 = base64.b64encode(hashlib.sha1(key+b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11").digest())
                t.send(b'HTTP/1.1 101 Switching Protocols\r\n')
                t.send(b'Upgrade: websocket\r\n')
                t.send(b'Connection: Upgrade\r\n')
                t.send(b'Sec-WebSocket-Accept: '+key2+b'\r\n\r\n')
                self.liste_connect.append(t)
                # on débloque demarre une fois la connexion WS établie
                if self.ws_actif is None:
                    self._verrou_ws.release()
                self.ws_actif=t
        print("Arrêt du serveur ws")
        if self._stopped:
            self._stop_handler()

    def _envoi(self, chaine:str):
        """
        envoie chaine en websocket
        """
        # TODO : exception pour attraper la fermeture de la page
        t=self.ws_actif
        taille = len(chaine)
        if t.fileno()!=-1:
            if taille < 126:
                return t.send(bytes([129,taille])+chaine.encode(encoding="utf-8"))
            elif taille < 65536:
                return t.send(bytes([129,126,taille//256,taille%256])+chaine.encode(encoding="utf-8"))
            else:
                liste = []
                for _ in range(8):
                    liste = [taille % 256]+liste
                    taille //=256
                liste = [129,127]+liste
                return t.send(bytes(liste)+chaine.encode(encoding="utf-8"))
        else:
            print("[_envoi]: ws off")

    def _push(self,o):
        """
        Envoie la représentation json d'un objet.
        Côté javascript, faire() prend en charge une liste de dictionnaires seulement.
        """
        data = json.dumps(o)
        if self.ready:
            self._envoi(data)
        else:
            self.pending.append(data)
            
    def draw(self,id_objet,img,x,y,size,clear=False):
        self._push([{"id":id_objet,"type":"draw","data":{"i":"../"+img,"x":x,"y":y,"s":size,"c":clear}}])
        
    def clear_canvas(self,id_objet,x,y,w,h):
        self._push([{"id":id_objet,"type":"clear","data":{"x":x,"y":y,"w":w,"h":h}}])
            
    def add_class(self,id_objet:str,classe:str):
        """
        Ajoute une classe à un objet de la page
        
        Paramètres:
            - id_objet: attribut id de l'objet
            
            - classe: classe à ajouter à l'objet
        """
        self._push([{"id":id_objet,"type":"class-a","data":classe}])
        
    def add_tmp_class(self,id_objet:str,classe:str,duration:int):
        """
        Ajoute temporairement une classe à un objet de la page
        
        Paramètres:
            - id_objet: attribut id de l'objet
            
            - classe: classe à ajouter temporairement
            
            - duration: durée pendant laquelle la classe est ajoutée
        """
        self._push([{"id":id_objet,"type":"class-t","data":{"c":classe,"t":duration}}])
        
    def remove_class(self,id_objet:str,classe:str):
        """
        Supprime une classe à un objet de la page
        
        Paramètres:
            - id_objet: attribut id de l'objet
            
            - classe: classe à supprimer de l'objet
        """
        self._push([{"id":id_objet,"type":"class-r","data":classe}])

    def attributs(self,id_objet,attr={},style={}):
        """
        Définit des attributs d'un objet de la page, identifié par son attribut id
        Paramètres:
          - id_objet: attribut id de l'objet
          - attr: dictionnaire {attribut:valeur} attribuant une nouvelle valeur à des attributs
          - style: dictionnaire {attribut:valeur} attribuant une nouvelle valeur à des attributs de style

        Valeur renvoyée : None
        """
        if attr != {}:
            self._push([{"id":id_objet,"type":"attributes","data":attr}])
        if style != {}:
            self._push([{"id":id_objet,"type":"style","data":{"style":style}}])
            
    def remove(self,id_objet:str):
        """
        Supprime un objet de la page
        
        Paramètres:
            - id_objet: attribut id de l'objet
        """
        self._push([{"id":id_objet,"type":"delete"}])
        
    def remove_children(self,id_objet:str):
        """
        Supprime tous les éléments dont l'objet est le parent
        
        Paramètres:
            -id_objet: attribut id de l'objet
        """
        self._push([{"id":id_objet,"type":"children"}])
    
    def change_text(self,id_objet:str,inner_text:str):
        """
        Change l'attribut inner_text de l'objet de la page
        
        Paramètres:
            - id_objet: attribut id de la page
            
            - inner_text: texte à remplacer
        """
        self._push([{"id":id_objet,"type":"content","data":inner_text}])

    def insere(self, id_objet:str,balise:str,attr:dict={},style:dict={},parent:str="body"):
        """
        Insère un élément sur la page, dans l'élément dont l'id est spécifié par parent

        Paramètres:
          - id_objet: attribut id de l'objet créé
          - balise: balise de l'objet créé
          - attr: dictionnaire {attribut:valeur} définissant les attributs de l'objet créé
          - style: dictionnaire {attribut:valeur} définissant les attributs de style de l'objet créé
          - parent: id de l'objet où insérer l'élément créé (default: body)

        Valeur renvoyée : None
        """
        l = []
        l.append({'id':'_nobj','type':'create','tagName':balise,'parent_id':parent,'data':{'id':id_objet}})
        if attr != {}:
            l.append({"id":id_objet,'type':'attributes',"data":attr})
        if style != {}:
            l.append({"id":id_objet,'type':'style',"data":{"style":style}})
        self._push(l)

    def injecte(self,code:str)->None:
        """
        Envoi du code javascript à l'interface, qui l'exécute
        
        Paramètres:
          - code: code javascript à exécuter

        Valeur renvoyée : None
        
        Exemple:
            Si la page web contient un élément <input> dont l'attribut id vaut "PIN",
            on peut récupérer sa valeur dans le programme python comme suit:
            
            # définir quoi faire de la valeur, ici l'afficher avec print
            interface.gestionnaire("recup_pin",lambda m,p: print(p))
            # envoi du code javascript faisant envoyer la valeur par la page
            interface.injecte('transmettre("recup_pin",PIN.value)')          
                """
        self._push([{'id':'_new_script','type':'create','tagName':'script','data':{'innerHTML':code}}])

    def _process(self,chaine:str):
        """
        chaine reçue via websocket
        """
    #    print("Données brutes :", chaine)
        try:
            data = json.loads(chaine)
        except:
            print("Erreur à l'analyse des données")
        
        if data[0] in ["**MD**","**MU**","**KD**","**KU**"] or (data[0] in self._handlers and self._handlers[data[0]] is not None):
            if data[0] in ["**MD**","**MU**","**KD**","**KU**"]:
                he = "_"+str.lower(data[0][2])+"h"
                hd = data[0][3]
            else:
                he = data[0]
                hd = data[0]

            handler,nonbloc = self._handlers[he]
            if nonbloc:
                handler_thread = threading.Thread(target=lambda : handler(hd,data[1]))
                self._threads_fils.append(handler_thread)
                handler_thread.start()
            else:
                try:
                    handler(hd,data[1])
                except StopInter:
#                    raise KeyboardInterrupt
                    pass
        else:
            print("Message :", data[0], "; Données :", data[1])