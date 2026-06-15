class _KEvent:
    """
    Evenement clavier
    """
    
    def __init__(self, state: str, keys: list, handler: callable):
        self.state = state
        self.keys = keys
        self.handler = handler
        
    # Ne regarde pas les touches de modification (Alt, Ctrl, Shift, etc.)
    def match(self, state: str, key: list):
        """
        Verifie si l'entree donnee correspond a cet evenement et l'appelle si c'est le cas
        Renvoie True si l'evenement correspond, False sinon
        """
        if state == self.state and key[5] in self.keys:
            self.handler(key[5])
            return True
        return False

from wsinter import Inter
class Keyboard:
    def __init__(self, web_manager: Inter):
        web_manager.gestionnaire_clavier(self.handle_input)
        
        self.pressed_keys = {}
        self.events = []

    def subscribe_event(self, handler: callable, state: str, keys: list):
        """
        Parametres :
            - handler: fonction appelee lorsque les conditions sont remplies
        
            - state: 
                - "D" si la touche est pressee
                - "U" si la touche est relachee
            
            - keys: liste de chaines de caractères représentant les touche declenchant l'evenement sur un clavier standard Qwerty
            
        Ajoute cet evenement a la liste des evenements
        """
        event = _KEvent(state, keys, handler)
        self.events.append(event)    
        
    def unsubscribe_event(self, handler: callable, state: str, keys: list):
        """
        Parametres :
            - handler: fonction appelee lorsque les conditions sont remplies
        
            - state: 
                - "D" si la touche est pressee
                - "U" si la touche est relachee
            
            - keys: liste de chaines de caractères représentant les touche declenchant l'evenement sur un clavier standard Qwerty
            
        Renvoie True s'il existait un tel evenement, False avec un message d'erreur sinon
        """
        event = _KEvent(state, keys, handler)
        try:
            self.events.remove(event)    
        except ValueError:
            print("ValueError: Aucun evenement de la sorte n'existe!")
            return False
        return True

    def handle_input(self, state: str, key: list):
        """
        Parametres:
            - state: 
                - "D" si la touche est pressee
                - "U" si la touche est relachee

            - key: La liste [altKey,ctrlKey,shiftKey,metaKey,key,code,repeat,timeStamp]
                - altKey,ctrlKey,shiftKey,metaKey : booléens indiquant si Alt, Control, Shift et Meta sont pressées
                - key : chaine de caractères représentant la saisie de caractère effectuée
                - code : chaine de caractères représentant la touche pressée sur un clavier standard Qwerty
                - repeat : booléen indiquant si la touche est en train d'être maintenue
                - timeStamp : entier donnant la chronologie des événements
            
        Redirige les evenements vers les bons gestionnaires
        """
        if state == "D":
            self.pressed_keys[key[5]] = key[5] in self.pressed_keys
        elif key[5] in self.pressed_keys.keys():
            del self.pressed_keys[key[5]]
            
        for event in self.events:
            event.match(state, key)
            
    def get_keys(self) -> dict:
        """
        Renvoie un dictionnaire contenant comme cles le code des touches appuyees en cet instant
        
        Les valeurs sont à True si et seulement si la touche est répétée
        
        On prend avantage du dictionnaire pour chercher plus facilement si une touche precise est appuyee
        """
        return self.pressed_keys
