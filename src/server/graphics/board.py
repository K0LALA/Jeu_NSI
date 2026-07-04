import sqlite3
import os # listdir
from math import ceil, floor

import web_helper
import collision_resolver
from constants import BOARD_PATH, TILESET_PATH_PLACEHOLDER, BLOCKS_SIZE, BASE_TILE_SIZE

# La taille d'une tile classique, sans zoom
TRANSLATE_AMOUNT = 16


class Board:
    def __init__(self, helper: web_helper.Helper, world: str, collision_resolver: collision_resolver.CollisionResolver, zoom: int = 2):
        """
        Parametres:
            - helper: L'instance Helper de la librairie web_helper
            
            - world: Le monde a charger
            
            - block_size: La taille en nombre de tiles de chaque bloc, defaut=16
            
            - tile_size: La taille en pixels de chaque tile sur la page, defaut=16
        """
        self.helper = helper
        self.world = world
        self.collision_resolver = collision_resolver
        self.zoom = zoom
        
        self.block_size = BLOCKS_SIZE
        # Ca depend des layers
        self.tile_pixel_sizes = {}
        self.block_pixel_sizes = {}
        self.collisions = {}
        
        self.layers: dict[int, str] = {}
        self.layer_bounds: dict[int, tuple[int]] = {}
        
        self.rendered_blocks: dict[set[tuple[int, int]]] = {}
                
        # On prete attention a la taille de board
        self.board_size = self.update_board_size()
        
        self.link = sqlite3.connect(BOARD_PATH, check_same_thread=False)
        self.base = self.link.cursor()
        
        # Coordonnees du centre en pixels
        self.base.execute("SELECT origin_x,origin_y FROM worlds WHERE name=?;", (self.world,))
        origin = self.base.fetchall()
        if len(origin) != 1:
            # Pour rajouter les colonnes:
            # `ALTER TABLE worlds ADD COLUMN {origin_x/origin_y} INTEGER;`
            self.link.close()
            raise ValueError("Il y a une erreur dans la base de données: Le monde n'a pas d'origine")
        self.origin = origin[0]
        self.shift = (0,0)
        
        # Liste les attributs des npc, ennemis et waypoints
        self.enemies_board = []
        self.npc_board = []
        self.waypoints_board = []

        self.champs_quete = {}
        self.etat_champs = {}

        # Ajoute les elements pour ce monde precis
        self.base.execute("SELECT layer_index,tileset,tiles_size,collisions,world FROM layers WHERE world=? ORDER BY layer_index ASC;", (self.world,))
        layers = self.base.fetchall()

        if layers == None:
            print("Ce monde n'a pas de couche!")
            self.link.close()
            return
        layers = [list(layer) for layer in layers]
        
        for layer in layers:
            # On map les couches avec leur tileset
            self.layers[layer[0]] = layer[1]
            self.tile_pixel_sizes[layer[0]] = layer[2]
            self.block_pixel_sizes[layer[0]] = layer[2] * BLOCKS_SIZE
            self.collisions[layer[0]] = layer[3]
            self.rendered_blocks[layer[0]] = set()
            
            # Pour chaque couche, on crée un div
            self.helper.ws.insere("layer_" + str(layer[0]), "div", style={"z-index": layer[0]}, parent="tiles")
        
        self.load()
        
    def update_board_size(self) -> tuple[float, float]:
        """
        Actualise les dimensions de la fenetre du navigateur pour self.board_size
        
        Renvoie le tuple (w,h) avec les dimensions de la fenetre du navigateur
        """
        size = self.helper.ws.get_window_size()
        # Pour savoir quels coefficients appliquer, se referer a editor.css
        w = size[0]
        h = size[1]
        self.board_size = (w, h)
        return self.board_size
    
    def calculate_shift(self, w, h):
        self.shift = (w / 2 - self.origin[0] * BASE_TILE_SIZE * self.zoom, h / 2 - self.origin[1] * BASE_TILE_SIZE * self.zoom)
        
    def get_block_id(self, layer: int, block_x: int, block_y: int) -> str:
        """
        Renvoie l'id du bloc spécifié sous forme de chaine de caractères
        """
        self.base.execute("SELECT block_id FROM blocks WHERE world=? AND layer_index=? AND block_x=? AND block_y=? LIMIT 1;", (self.world, layer, block_x, block_y))
        block = self.base.fetchone()
        if block == None:
            return None
        return str(block[0])
    
    def render_block(self, block_id, layer, block_x, block_y):
        """
        Affiche toutes les tiles comprises dans un bloc
        
        Le seul appel au SGBD est pour recuperer toutes les tiles du bloc, non pour recuperer sa couche ou sa position
        
        Parametres:
            - block_id: L'id du bloc dans le SGBD
            
            - layer: Couche du bloc dans le monde
            
            - block_x,block_y: Position du bloc dans le monde
        """        
        block_offset = ((block_x) * self.block_pixel_sizes[layer], (block_y) * self.block_pixel_sizes[layer])
        self.base.execute("SELECT x,y,image_name FROM tiles WHERE block_id=?;", (block_id,))
        tiles = self.base.fetchall()

        if len(tiles) > 0:
            #self.helper.ws.insere(block_id, "div", parent="layer_" + str(layer))
            self.helper.ws.insere(block_id, "canvas", \
                attr={"width":self.block_pixel_sizes[layer] * self.zoom,"height":self.block_pixel_sizes[layer] * self.zoom}, \
                style={"left":str(block_offset[0] * self.zoom)+"px","top":str(block_offset[1] * self.zoom)+"px"}, \
                parent="layer_" + str(layer))
            self.rendered_blocks[layer].add((block_x, block_y))
        
        for tile in tiles:
            img_id = "_".join(map(str, [layer, block_x * self.block_size + tile[0], block_y * self.block_size + tile[1]]))
            img_path = TILESET_PATH_PLACEHOLDER.replace("%SET%", self.layers[layer]).replace("%IMG%", tile[2])
            position = (self.zoom * (block_offset[0] + tile[0] * self.tile_pixel_sizes[layer]), self.zoom * (block_offset[1] + tile[1] * self.tile_pixel_sizes[layer]))
            #self.helper.add_image_id(img_id, img_path, position, (self.zoom * self.tile_pixel_sizes[layer], self.zoom * self.tile_pixel_sizes[layer]), parent=block_id)
            self.helper.ws.draw(block_id, img_path, tile[0] * self.tile_pixel_sizes[layer] * self.zoom, tile[1] * self.tile_pixel_sizes[layer] * self.zoom, self.tile_pixel_sizes[layer] * self.zoom)
            if img_path == "assets/tilesets/x16_decorations/x16_decorations_060.png" or img_path == "assets/tilesets/x16_decorations/x16_decorations_061.png" or img_path == "assets/tilesets/x16_decorations/x16_decorations_067.png" or img_path == "assets/tilesets/x16_decorations/x16_decorations_068.png" or img_path == "assets/tilesets/x16_decorations/x16_decorations_058.png" or img_path == "assets/tilesets/x16_decorations/x16_decorations_059.png"  or img_path == "assets/tilesets/x16_decorations/x16_decorations_065.png" or img_path == "assets/tilesets/x16_decorations/x16_decorations_066.png":
                self.champs_quete[img_id] = img_path
        for cle in self.champs_quete:
            if self.champs_quete[cle] == "assets/tilesets/x16_decorations/x16_decorations_068.png" or self.champs_quete[cle] == "assets/tilesets/x16_decorations/x16_decorations_066.png" :
                self.etat_champs[(int(cle.split("_")[1]), int(cle.split("_")[2]))] = True
            else:
                self.etat_champs[(int(cle.split("_")[1]), int(cle.split("_")[2]))] = False
        
        self.base.execute("SELECT enemy_id,x,y FROM enemies WHERE block_id=?;", (block_id,))
        for elt in self.base.fetchall():
            self.enemies_board.append(elt)

        self.base.execute("SELECT npc_id,x,y,npc_image,npc_name FROM NPCs WHERE block_id=?;", (block_id,))
        for elt in self.base.fetchall():
            self.npc_board.append(elt)

        self.base.execute("SELECT waypoint_id,x,y,destination FROM waypoints WHERE block_id=?;", (block_id,))
        for elt in self.base.fetchall():
            self.waypoints_board.append(elt)
    
    def add_block(self, layer, block_x, block_y) -> int:
        """
        Ajoute un div sur la page HTML pour le bloc

        Si le bloc n'existe pas dans la base de données, il n'est pas cree !
        
        Parametres:
            - layer: Couche du bloc
            
            - block_x,block_y: Position du bloc
            
        Les parametres permettent de determiner le block_id
        
        Renvoie le block_id
        """
        block_id = self.get_block_id(layer, block_x, block_y)
        if block_id == None:
            return
        
        self.render_block(block_id, layer, block_x, block_y)
        
        return block_id

    def get_block_presence(self, block_id, x, y, size):
        """
        Fonction récursive, qui pour le bloc donné va jusqu'à une taille de 1 et renvoie un tuple de la forme (bool, (bool, ..., ..., ..., ...), (...), (...), (...)) selon s'il y a un bloc ou non
        """
        if size == 1:
            self.base.execute("SELECT x FROM tiles WHERE block_id=? AND x=? AND y=?;", (block_id, x, y))
            return [len(self.base.fetchall()) == 1]
        half_size = size // 2
        b7 = self.get_block_presence(block_id, x, y, half_size)
        b9 = self.get_block_presence(block_id, x + half_size, y, half_size)
        b1 = self.get_block_presence(block_id, x, y + half_size, half_size)
        b3 = self.get_block_presence(block_id, x + half_size, y + half_size, half_size)
        return (b1[0] or b3[0] or b7[0] or b9[0], b7, b9, b1, b3)

    def get_block_lods(self, layer: int, block_x: int, block_y: int) -> tuple[bytes | list[bool]]:
        """
        Pour le bloc spécifié, effectue un pré-traitement pour savoir où il y a des blocs afin que la recherche de collisions soit plus rapide
        """
        self.base.execute("SELECT block_id FROM blocks WHERE block_x=? AND block_y=? AND world=? AND layer_index=? LIMIT 1;", (block_x, block_y, self.world, layer))
        block = self.base.fetchone()
        if block == None:
            return
        
        return self.get_block_presence(block[0], 0, 0, BLOCKS_SIZE)

    def add_collider_block(self, layer, block_x, block_y, bps):
        position = (block_x * bps, block_y * bps, bps * (block_x + 1) - 1, bps * (block_y + 1) - 1)
        lods = self.get_block_lods(layer, block_x, block_y)
        if lods != None:
            block_id = self.get_block_id(layer, block_x, block_y)
            self.rendered_blocks[layer].add((block_x, block_y))
            self.collision_resolver.add_block(block_id, position, lods)

    def add_collider_layer(self, layer: int):
        """
        Ajoute une couche de collisionneurs au collision_resolver
        
        Paramètres:
            - layer: Entier donnant la couche de collisionneurs
            
            - center_block: Tuple d'entiers donnant les coordonnées du bloc qui doit être placé au centre
        """
        w,h = self.board_size
        block_size = self.block_pixel_sizes[layer] * self.zoom
        left = (-self.shift[0]) / block_size
        right = (w - self.shift[0]) / block_size
        
        top = (-self.shift[1]) / block_size
        bottom = (h - self.shift[1]) / block_size
        
        min_x = floor(left)
        max_x = ceil(right)
        
        min_y = floor(top)
        max_y = ceil(bottom)
        
        for block_x in range(min_x, max_x + 1):
            for block_y in range(min_y, max_y + 1):
                self.add_collider_block(layer, block_x, block_y, block_size)
        
        return (min_x, min_y, max_x, max_y)

    def add_layer(self, layer: int):
        """
        Charge le layer specifie sur la page en centrant sur le block donne 
        """
        # On récupère la taille de la fenetre
        w,h = self.board_size
        block_size = self.block_pixel_sizes[layer] * self.zoom
        left = (-self.shift[0]) / block_size
        right = (w - self.shift[0]) / block_size
        
        top = (-self.shift[1]) / block_size
        bottom = (h - self.shift[1]) / block_size
        
        min_x = floor(left)
        max_x = ceil(right)
        
        min_y = floor(top)
        max_y = ceil(bottom)

        for block_x in range(min_x, max_x + 1):
            for block_y in range(min_y, max_y + 1):
                self.add_block(layer, block_x, block_y)
                
        return (min_x, min_y, max_x, max_y)

    def load(self):
        """
        Charge toute la carte spécifiée sur la page en centrant aux coordonnées données
        """
        w,h = self.update_board_size()
        self.calculate_shift(w,h)
        self.helper.ws.attributs("tiles", style={"left": str(self.shift[0]) + "px", "top": str(self.shift[1]) + "px"})
        for layer in self.layers.keys():
            if self.collisions[layer]:
                # Il n'est pas nécessaire de vérifier si self.collisions est à None car c'est le cas seulement si board est EditorBoard, auquel cas load_all est surchargé
                self.layer_bounds[layer] = self.add_collider_layer(layer)
                continue
            self.layer_bounds[layer] = self.add_layer(layer)

    def remove_block(self, layer: int, block_x: int, block_y: int, collider: bool) -> None:
        """
        Enlève un bloc de l'affichage ET de la logique s'il y est bien
        """
        block_id = self.get_block_id(layer, block_x, block_y)
        if block_id == None or not (block_x, block_y) in self.rendered_blocks[layer]:
            return
        
        self.rendered_blocks[layer].remove((block_x, block_y))
        if collider:
            if isinstance(self, EditorBoard):
                self.helper.ws.remove(block_id)
            else:
                self.collision_resolver.remove_block(block_id)
        else:
            self.helper.ws.remove(block_id)

    def update_displayed_blocks(self):
        """
        Cette fonction doit après un mouvement de la carte, afficher de nouveaux blocs et supprimer les anciens
        
        Étant donné que les mouvements sont petits (même pour l'éditeur ?), on peut se contenter de regarder qu'une couche en plus de celle actuelle
        """
        w,h = self.update_board_size()
        for layer in self.layers:
            collider = self.collisions[layer]
            bounds = self.layer_bounds[layer]
            block_size = self.block_pixel_sizes[layer] * self.zoom
            
            left = (-self.shift[0]) / block_size
            right = (w - self.shift[0]) / block_size
            
            top = (-self.shift[1]) / block_size
            bottom = (h - self.shift[1]) / block_size
            
            min_x = floor(left)
            max_x = ceil(right)
            
            min_y = floor(top)
            max_y = ceil(bottom)
            
            if (min_x, min_y, max_x, max_y) == bounds:
                continue
            
            now_rendered_blocks = set()
            
            for block_x in range(min_x, max_x + 1):
                for block_y in range(min_y, max_y + 1):
                    now_rendered_blocks.add((block_x, block_y))
                    
            to_add = now_rendered_blocks - self.rendered_blocks[layer]
            to_remove = self.rendered_blocks[layer] - now_rendered_blocks

            for x, y in to_add:
                (self.add_collider_block(layer, x, y, block_size) if (collider and not isinstance(self, EditorBoard)) else self.add_block(layer, x, y))
            
            for x, y in to_remove:
                self.remove_block(layer, x, y, collider)
                
    def translate(self, move: tuple):
        """
        Bouge la carte en utilisant le vecteur move, on bouge en utilisant le nombre de pixels dans move
        """
        if move == [0, 0]:
            return
        ox,oy = self.shift
        mx = move[0]
        my = move[1]
        
        self.shift = (ox + mx, oy + my)
        
        self.update_displayed_blocks()
        
        self.helper.ws.attributs("tiles", style={"left": str(self.shift[0]) + "px", "top": str(self.shift[1]) + "px"})

    def window_size_changed(self):
        """
        Fonction à appeler lorsque la taille de la fenêtre change, cela permet de garder le joueur à la même position, et de cacher / afficher les blocs invisibles / visibles maintenant
        """
        ow,oh = self.board_size
        w,h = self.update_board_size()
        self.shift = (self.shift[0] + (w - ow) / 2, self.shift[1] + (h - oh) / 2)
        self.helper.ws.attributs("tiles", style={"left": str(self.shift[0]) + "px", "top": str(self.shift[1]) + "px"})
        self.update_displayed_blocks()
        
    def reset_view(self):
        w,h = self.board_size
        self.calculate_shift(w,h)
        self.helper.ws.attributs("tiles", style={"left": str(self.shift[0]) + "px", "top": str(self.shift[1]) + "px"})
        self.update_displayed_blocks()


class EditorBoard(Board):
    def __init__(self, helper: web_helper.Helper, world: str):
        super().__init__(helper, world, None)
        layers = []
        for l in self.layers.keys():
            layers.append([l, self.layers[l], self.tile_pixel_sizes[l], self.collisions[l]])
        self.helper.ws.injecte("addLayers(" + str(layers) + ")")

        self.layer: int = 0
        self.tile: str = ""
        self.tool: str = "draw"
        
        # Coordonnees pour la selection, un tuple lorsque actif et None lorsque rien (bien vu l'artiste)
        self.p1: tuple[tuple[int, int], tuple[int, int]] = None
        self.p2: tuple[tuple[int, int], tuple[int, int]] = None

        # Utilises pour action, qui devrait sinon en initialiser beaucoup trop
        self.link = sqlite3.connect(BOARD_PATH, check_same_thread=False)
        self.base = self.link.cursor()
        self.commit = False
        
        
    def update_board_size(self) -> tuple[float, float]:
        size = self.helper.ws.get_window_size()
        # Pour savoir quels coefficients appliquer, se referer a editor.css
        w = size[0] * 0.8
        h = size[1] * 0.85
        self.board_size = (w, h)
        return self.board_size
    
    def window_size_changed(self):
        ow,oh = self.board_size
        w,h = self.update_board_size()
        self.shift = (self.shift[0] + (w - ow) / 2, self.shift[1] + (h - oh) / 2)
        self.helper.ws.attributs("tiles", style={"left": str(self.shift[0]) + "px", "top": str(self.shift[1]) + "px"})
        self.update_displayed_blocks()
        self.helper.ws.attributs("board", style={"background-position-x": str(self.shift[0]) + "px"\
                                                ,"background-position-y": str(self.shift[1]) + "px"})
    
    def load(self):
        """
        Charge toute la carte specifiee sur la page en centrant au coordonnees donnees
        
        Les couches de collisions sont affichées
        """
        w,h = self.update_board_size()
        self.calculate_shift(w, h)
        self.helper.ws.attributs("tiles", style={"left": str(self.shift[0]) + "px", "top": str(self.shift[1]) + "px"})
        self.helper.ws.attributs("board", style={"background-position-x": str(self.shift[0]) + "px"\
                                                ,"background-position-y": str(self.shift[1]) + "px"})
        for layer in self.layers.keys():
            self.layer_bounds[layer] = self.add_layer(layer)
        
    # Methodes pour l'interaction PAGE -> BOARD
    
    def layer_changed(self, _, o: int):
        self.layer = int(o)
        self.tile = ""
        
        # On supprime tout d'abord
        self.helper.ws.remove_children("tileset")
        
        tileset_path = "/assets/tilesets/" + self.layers[self.layer] + "/"
        # Charge les images
        i = 0
        for file in sorted(os.listdir("content" + tileset_path)):
            self.helper.ws.insere("palette_" + str(i), "img", attr={'src':'../' + tileset_path + file}, parent="tileset")
            i += 1

        if i == 1:
            self.tile = file
            
        self.helper.ws.injecte("addTilesEvent();")
        
    def tile_changed(self, _, o):
        self.tile = o
        if self.tool == "select" and self.p1 != None and self.p2 != None:
            self.selection(self.tile)
        
    def create_layer(self, _, o: list[str]):
        index,tileset,size,has_collisions = o
        index = int(index)
        size = int(size)
        has_collisions = bool(has_collisions)
        
        self.layers[index] = tileset
        self.tile_pixel_sizes[index] = size
        self.block_pixel_sizes[index] = size * BLOCKS_SIZE
        self.collisions[index] = has_collisions
        self.rendered_blocks[index] = set()
        self.layer_bounds[index] = self.add_layer(index)
        
        self.base.execute("INSERT INTO layers VALUES (?,?,?,?,?);", (self.world, index, tileset, size, has_collisions))
        self.link.commit()
        
        self.helper.ws.insere("layer_" + str(index), "div", style={"z-index": index * 2}, parent="tiles")
        
    def delete_layer(self, _, o):
        if self.layer != int(o):
            raise ValueError("Il y a un probleme de synchronisation entre le client et le serveur, relancez.")
        
        self.helper.ws.remove("layer_option_" + str(self.layer))
        self.helper.ws.remove("layer_" + str(self.layer))
        del self.layers[self.layer]
        del self.tile_pixel_sizes[self.layer]
        del self.block_pixel_sizes[self.layer]
        
        self.base.execute("DELETE FROM layers WHERE world=? AND layer_index=?;", (self.world, self.layer))
        self.link.commit()
        
    def tool_changed(self, _m, o):
        """
        Cette méthode est appelée lorsque l'outil est changé, via un gestionnaire d'événements WsInter
        
        Lorsque l'outil de sélection était sélectionné et que la gomme vient d'être cliquée
        """
        if self.tool == "select" and o == "erase" and self.p1 != None and self.p2 != None:
            self.selection("__erase__")
            return
        self.tool = o
        # Permet de reset la selection, par exemple en appuyant a nouveau sur le bouton de selection
        self.p1 = None
        self.p2 = None
        self.helper.ws.add_class("corner-1", "hidden")
        self.helper.ws.add_class("corner-2", "hidden")
        
    def translate_direction(self, move: tuple):
        """
        Bouge la carte en utilisant les directions donnees par le vecteur move, on bouge en utilisant TRANSLATE_AMOUNT
        """
        if move == [0, 0]:
            return
        self.translate((move[0] * BASE_TILE_SIZE, move[1] * BASE_TILE_SIZE))
        self.helper.ws.attributs("board", style={"background-position-x": str(self.shift[0]) + "px"\
                                                ,"background-position-y": str(self.shift[1]) + "px"})

    def get_block_id_or_create(self, block_x: int, block_y: int, create: bool = False) -> str:
        """
        Renvoie l'id du bloc dans la base de donnees et le cree si create est a True
        
        S'il n'y a pas de tel bloc, renvoie None.
        
        Parametres:
            - (block_x, block_y): Les coordonnees du bloc
            
            - create: True si bloc doit être créé lorsqu'il n'existe pas, False sinon
        """
        block_id = self.get_block_id(self.layer, block_x, block_y)
        
        if block_id == None and create:
            # On crée un nouveau bloc
            self.base.execute("INSERT INTO blocks(world,layer_index,block_x,block_y) VALUES (?,?,?,?);", (self.world, self.layer, block_x, block_y))
            self.base.execute("SELECT block_id FROM blocks WHERE world=? AND layer_index=? AND block_x=? AND block_y=?;", (self.world, self.layer, block_x, block_y))
            block_id = self.base.fetchone()[0]
            self.helper.ws.insere(block_id, "canvas", \
                attr={"width":self.block_pixel_sizes[self.layer] * self.zoom,"height":self.block_pixel_sizes[self.layer] * self.zoom}, \
                style={"left":str(block_x * self.block_pixel_sizes[self.layer] * self.zoom)+"px","top":str(block_y * self.block_pixel_sizes[self.layer] * self.zoom)+"px"}, \
                parent="layer_" + str(self.layer))
            
        return block_id
    
    def add_or_edit_tile(self, block_id: str, block_pos: tuple, block_offsets: tuple, tile_pos: tuple) -> None:
        """
        Ajoute ou modifie une tile a la position donnee
        
        La tile utilisee pour dessiner est celle contenue dans self.tile[:-4]
        
        Parametres:
            - block_id: L'id du bloc dans lequel est la tile, on suppose qu'il existe dans la base de donnee
            
            - block_pos: Les coordonnees (x,y) du bloc
            
            - block_offsets: Les decalages (w,h) en pixels pour le bloc
            
            - tile_pos: Les coordonnees de la tile dans le bloc
        """
        self.base.execute("SELECT COUNT(image_name) FROM tiles WHERE block_id=? AND x=? AND y=?;", (block_id, tile_pos[0], tile_pos[1]))
        res = self.base.fetchall()[0][0]
        path = TILESET_PATH_PLACEHOLDER.replace("%SET%", self.layers[self.layer]).replace("%IMG%", self.tile[:-4])
        if res > 1:
            raise ValueError("Plusieurs tiles existent")
        elif res == 0:
            # On cree une nouvelle tile
            self.base.execute("INSERT INTO tiles VALUES (?,?,?,?);", (block_id, tile_pos[0], tile_pos[1], self.tile[:-4]))
            self.helper.ws.draw(block_id, path, tile_pos[0] * self.tile_pixel_sizes[self.layer] * self.zoom, tile_pos[1] * self.tile_pixel_sizes[self.layer] * self.zoom, self.tile_pixel_sizes[self.layer] * self.zoom)
        else:
            # On modifie la tile d'avant
            self.helper.ws.draw(block_id, path, tile_pos[0] * self.tile_pixel_sizes[self.layer] * self.zoom, tile_pos[1] * self.tile_pixel_sizes[self.layer] * self.zoom, self.tile_pixel_sizes[self.layer] * self.zoom, clear=True)
            self.base.execute("UPDATE tiles SET image_name = ? WHERE block_id=? AND x=? AND y=?;", (self.tile[:-4], block_id, tile_pos[0], tile_pos[1]))
            
    def remove_tile(self, block_id: str, tile_pos: tuple):
        self.helper.ws.clear_canvas(block_id, tile_pos[0] * self.tile_pixel_sizes[self.layer] * self.zoom, tile_pos[1] * self.tile_pixel_sizes[self.layer] * self.zoom, self.tile_pixel_sizes[self.layer] * self.zoom, self.tile_pixel_sizes[self.layer] * self.zoom)
        self.base.execute("DELETE FROM tiles WHERE block_id=? AND x=? AND y=?;", (block_id, tile_pos[0], tile_pos[1]))
    
    def adjust_selection(self):
        """
        Renvoie un tuple (c1, c2) avec c1 et c2 respectivement les coins haut-gauche et bas-droit, peu importe self.p1 et self.p2
        """

        x1 = self.p1[0][0] * self.block_size + self.p1[1][0]
        y1 = self.p1[0][1] * self.block_size + self.p1[1][1]
        
        x2 = self.p2[0][0] * self.block_size + self.p2[1][0]
        y2 = self.p2[0][1] * self.block_size + self.p2[1][1]

        if x1 < x2:
            min_x = (self.p1[0][0], self.p1[1][0])
            max_x = (self.p2[0][0], self.p2[1][0])
        else:
            min_x = (self.p2[0][0], self.p2[1][0])
            max_x = (self.p1[0][0], self.p1[1][0])

        if y1 < y2:
            min_y = (self.p1[0][1], self.p1[1][1])
            max_y = (self.p2[0][1], self.p2[1][1])
        else:
            min_y = (self.p2[0][1], self.p2[1][1])
            max_y = (self.p1[0][1], self.p1[1][1])
            
        c1 = ((min_x[0], min_y[0]), (min_x[1], min_y[1]))
        c2 = ((max_x[0], max_y[0]), (max_x[1], max_y[1]))
        
        return (c1, c2)
    
    def selection(self, tile: str):
        """
        Fait une action sur la zone selectionnee
        
        Parametres:
            - tile: Une chaine de caracteres qui represente soit une tile, soit __erase__ et qui sert a effacer toute la zone
        """
        assert self.p1 != None and self.p2 != None, "La selection n'est pas complete"
        
        corner1, corner2 = self.adjust_selection()
        
        create = tile != "__erase__"
        
        tile_x = corner1[1][0]
        tile_y = corner1[1][1]
        
        block_x = corner1[0][0]
        block_y = corner1[0][1]
        current_block_id = self.get_block_id_or_create(block_x, block_y, create=True)
        
        x_count = (corner2[0][0] * self.block_size + corner2[1][0]) - (corner1[0][0] * self.block_size + corner1[1][0])
        y_count = (corner2[0][1] * self.block_size + corner2[1][1]) - (corner1[0][1] * self.block_size + corner1[1][1])

        block_offset_x = block_x * self.block_pixel_sizes[self.layer] * self.zoom
        block_offset_y = block_y * self.block_pixel_sizes[self.layer] * self.zoom
        
        for _ in range(x_count + 1):
            for _ in range(y_count + 1):
                if current_block_id == None:
                    continue
                
                if tile == "__erase__":
                    self.remove_tile(current_block_id, (tile_x, tile_y))
                else: 
                    self.add_or_edit_tile(current_block_id, (block_x, block_y), (block_offset_x, block_offset_y), (tile_x, tile_y))
                
                tile_y += 1
                if tile_y == self.block_size:
                    block_y += 1
                    current_block_id = self.get_block_id_or_create(block_x, block_y, create=create)
                    block_offset_x = block_x * self.block_pixel_sizes[self.layer] * self.zoom
                    block_offset_y = block_y * self.block_pixel_sizes[self.layer] * self.zoom
                    tile_y = 0
            
            tile_x += 1
            if tile_x == self.block_size:
                block_x += 1
                tile_x = 0
            tile_y = corner1[1][1]
            block_y = corner1[0][1]
            current_block_id = self.get_block_id_or_create(block_x, block_y, create=create)
            block_offset_x = block_x * self.block_pixel_sizes[self.layer] * self.zoom
            block_offset_y = block_y * self.block_pixel_sizes[self.layer] * self.zoom

    def action(self, button: str, click_pos: tuple):
        """
        Lorsqu'un bouton de la souris est appuye sur board
        
        Parametres:
            - button: Le bouton qui a ete appuye, parmi ['L', 'R', 'M'] respectivement pour Gauche, Droite et Milieu
            
            - click_pos: La position en pixels sur la page du clic
        """
        def add(block_pos, block_offsets, tile_pos):
            """
            Cette methode ajoute une tile a la position donnee sur la page et actualise la base de donnees, elle ajoute un bloc si necessaire
            """
            block_id = self.get_block_id_or_create(block_pos[0], block_pos[1], create=True)
            self.add_or_edit_tile(block_id, block_pos, block_offsets, tile_pos)
                        
        def remove(block_pos, tile_pos):
            """
            Cette methode supprime la tile specifiee de la page et actualise la base de donnees
            """
            block_id = self.get_block_id_or_create(block_pos[0], block_pos[1])
            self.remove_tile(block_id, tile_pos)

        if self.link == None:
            self.link = sqlite3.connect(BOARD_PATH)
            self.commit = True
            try:
                self.link.autocommit = True
            except AttributeError:
                print("L'attribut autocommit n'est pas disponible pour sqlite3")
                self.commit = False
            self.base = self.link.cursor()
        
        x,y = click_pos[0] - int(self.shift[0]), click_pos[1] - int(self.shift[1])
        
        block_x = x // (self.block_pixel_sizes[self.layer] * self.zoom)
        block_y = y // (self.block_pixel_sizes[self.layer] * self.zoom)
        
        block_offset_x = block_x * self.block_pixel_sizes[self.layer] * self.zoom
        block_offset_y = block_y * self.block_pixel_sizes[self.layer] * self.zoom
        
        tile_x = (x - block_offset_x) // (self.tile_pixel_sizes[self.layer] * self.zoom)
        tile_y = (y - block_offset_y) // (self.tile_pixel_sizes[self.layer] * self.zoom)
        
        match self.tool:
            case 'draw':
                if button == 'L' and self.tile != "":
                    add((block_x, block_y), (block_offset_x, block_offset_y), (tile_x, tile_y))
                elif button == 'R':
                    remove((block_x, block_y), (tile_x, tile_y))
            case 'erase':
                remove((block_x, block_y), (tile_x, tile_y))
            case 'select':
                # Une fois qu'une zone est selectionnee, il suffit d'appuyer sur la gomme ou une tile afin que toute la zone soit affectee par soit la gomme soit une tile
                pos = ((block_x, block_y), (tile_x, tile_y))
                page_pos = (self.zoom * (tile_x * self.tile_pixel_sizes[self.layer]) + block_offset_x, self.zoom * (tile_y * self.tile_pixel_sizes[self.layer]) + block_offset_y)
                if button == 'L':
                    self.p1 = pos
                    self.helper.ws.remove_class("corner-1", "hidden")
                    self.helper.ws.attributs("corner-1", style={"width":str(self.tile_pixel_sizes[self.layer] * self.zoom) + "px", "height": str(self.tile_pixel_sizes[self.layer] * self.zoom) + "px", "left": str(page_pos[0]) + "px", "top": str(page_pos[1]) + "px"})
                if button == "R":
                    self.p2 = pos
                    self.helper.ws.remove_class("corner-2", "hidden")
                    self.helper.ws.attributs("corner-2", style={"width":str(self.tile_pixel_sizes[self.layer] * self.zoom) + "px", "height": str(self.tile_pixel_sizes[self.layer] * self.zoom) + "px", "left": str(page_pos[0]) + "px", "top": str(page_pos[1]) + "px"})
            case _:
                raise TypeError("Il n'existe pas d'outil de ce type")
