import os # remove
import time # time
import threading # Threading
from math import sqrt
from random import randint

import wsinter
import web_helper
import collision_resolver

import graphics.board
from characters.character import Character
from characters.player import Player
from characters.enemy import Enemy
from characters.npc import Interactable, Npc
from inputs.keyboard import Keyboard
from inputs.mouse import Mouse

import constants

game = None

def main():
    global game

    try:
        lock = open("launched", "x")
        lock.close()
    except FileExistsError:
        raise FileExistsError("Une instance du serveur est deja lancee")

    game = Game("index.html")

def stop():
    global game
    game.stop()

    os.remove("launched")
    exit(0)

class Game:
    def __init__(self, start_page: str = "index.html"):
        """
        Point d'entree du programme quand on lance le serveur
        """
        self.web_manager = wsinter.Inter("content/pages/" + start_page)
        self.web_manager.demarre(clavier=True)

        self.web_helper = web_helper.Helper(self.web_manager)
        
        # On attend que la page soit prête, surtout pour la taille de la page
        while not self.web_manager.ready:
            time.sleep(0.01)

        # Gestionnaires inputs
        self.keyboard_manager = Keyboard(self.web_manager)
        self.mouse_manager = Mouse(self.web_manager)

        self.collision_resolver = collision_resolver.CollisionResolver()
        self.board = graphics.board.Board(self.web_helper, "spawn", self.collision_resolver)
        
        self.splayer = Character(self.web_helper, "player", (600, 350), "player")
        
        # Pour l'instant, le joueur doit rester en premier, car il a du style sur #img0
        # Les coordonnées qui lui sont passées sont celles
        self.init_player(self.board.origin, 7)


        self.zoom = self.board.zoom
        self.npc: list[Npc] = []

        for npc in self.board.npc_board:
            position = (npc[1]*constants.BASE_TILE_SIZE*self.zoom, npc[2]*constants.BASE_TILE_SIZE*self.zoom)
            position_collider = ((npc[1]*constants.BASE_TILE_SIZE*self.zoom)-50, (npc[2]*constants.BASE_TILE_SIZE*self.zoom)-50, (npc[1]*constants.BASE_TILE_SIZE*self.zoom)+50, (npc[2]*constants.BASE_TILE_SIZE*self.zoom)+50)
            current_npc = Npc(self.web_helper, position, "assets/spritesheets/blue_haired_woman/"+str(npc[3]), dialogs=str(npc[4]))
            self.collision_resolver.add_collider(position_collider, collision_resolver.INTERACTABLE, current_npc)
            self.npc.append(current_npc)

        
        self.enemies: list[Enemy] = []

        for enemy in self.board.enemies_board:
            position = (enemy[1]*constants.BASE_TILE_SIZE*self.zoom, enemy[2]*constants.BASE_TILE_SIZE*self.zoom)
            current_enemy = Enemy(self.web_helper, position, "assets/spritesheets/blonde_man/blonde_man_010.png", 3)
            self.enemies.append(current_enemy)

        self.interactable: Interactable = None

        self.keyboard_manager.subscribe_event(self.interact_key_handler, "D", ['KeyE', 'ArrowUp', 'ArrowLeft', 'ArrowDown', 'ArrowRight', 'Enter'])

        # On lance la boucle principale
        self.loop_thread = threading.Thread(target=self.loop)
        self.loop_thread.start()

        self.menu_cooldown = 0.5
        self.last_menu_time = time.time()
        self.menu = False

        self.tickspeed = 113

        self.inventaire = {}
        self.place_inventaire = {}

    def init_player(self, position: tuple[int, int], zindex: int):
        self.player = Player(self.web_helper, position)
        self.web_manager.attributs(self.player.id, style={"z-index": zindex})

    def interact_key_handler(self, key):
        if self.interactable == None or not issubclass(type(self.interactable), Interactable):
            return
        match key:
            case 'KeyE':
                if not self.interactable.is_opened():
                    self.interactable.interact()
            case 'ArrowUp' | 'ArrowLeft' | 'ArrowDown' | 'ArrowRight' | 'Enter':
                if self.interactable.is_opened():
                    self.interactable.key(key)

    def loop(self):
        """
        Contient la boucle principale

        On vise 60 images par secondes, donc 60 iterations par seconde, faire plus serait consommer beaucoup de ressources pour pas grand chose

        Pour la physique on pourrait meme viser 30 iterations par seconde

        Ainsi on conditionne le temps
        """
        self.do_loop = True
        last_loop_time = time.time()

        while self.do_loop:
            delta_time = time.time() - last_loop_time - 0.017
            # 1 / 60 ~= 0.017, on s'embete pas à faire le calcul tout le temps, on pourrait limite stocker la duree dans une variable mais pas tres utile non plus
            if delta_time < 0:
                time.sleep(-delta_time / 3)
                continue
            
            delta_time += 0.017
            last_loop_time = time.time()
            
            window_size = self.web_manager.get_window_size_if_changed()
            
            if window_size != None:
                self.board.window_size_changed()
                self.player.update_graphics(window_size)

            keys = self.keyboard_manager.get_keys()
            
            if 'KeyP' in keys and self.player.is_dead():
                self.web_manager.remove_children("player")
                self.init_player(self.board.origin, 7)
                self.board.reset_view()

            if "KeyI" in keys and time.time() - self.last_menu_time >= self.menu_cooldown:
                self.menu = not self.menu
                self.last_menu_time = time.time()
                if self.menu == True :
                    self.web_manager.attributs("menu",{}, style={"visibility": "visible"})
                else:
                    self.web_manager.attributs("menu",{}, style={"visibility": "hidden"})

            # On actualise la liste des ennemis en supprimant ceux qui sont morts
            for enemy in self.enemies:
                if enemy.is_dead():
                    self.enemies.remove(enemy)

            # Toutes les instructions ici sont mises en pauses lorsqu'un menu est ouvert par le joueur
            new_interactable = -1
            if (self.interactable is None or not self.interactable.is_opened()) and self.menu == False :
                x = randint(-44, -37)
                y = randint(-4, 10)
                if randint(1, self.tickspeed) == 1 :
                    if "2_"+str(x)+"_"+str(y) in self.board.champs_quete :
                        if self.board.champs_quete["2_"+str(x)+"_"+str(y)] == "assets/tilesets/x16_decorations/x16_decorations_060.png" :
                            self.web_helper.change_image("2_"+str(x)+"_"+str(y), "assets/tilesets/x16_decorations/x16_decorations_061.png")
                            self.board.champs_quete["2_"+str(x)+"_"+str(y)] = "assets/tilesets/x16_decorations/x16_decorations_061.png"
                            self.tickspeed -= 1
                        elif self.board.champs_quete["2_"+str(x)+"_"+str(y)] == "assets/tilesets/x16_decorations/x16_decorations_061.png" :
                            self.web_helper.change_image("2_"+str(x)+"_"+str(y), "assets/tilesets/x16_decorations/x16_decorations_067.png")
                            self.board.champs_quete["2_"+str(x)+"_"+str(y)] = "assets/tilesets/x16_decorations/x16_decorations_067.png"
                            self.tickspeed -= 1
                        elif self.board.champs_quete["2_"+str(x)+"_"+str(y)] == "assets/tilesets/x16_decorations/x16_decorations_067.png" :
                            self.web_helper.change_image("2_"+str(x)+"_"+str(y), "assets/tilesets/x16_decorations/x16_decorations_068.png")
                            self.board.champs_quete["2_"+str(x)+"_"+str(y)] = "assets/tilesets/x16_decorations/x16_decorations_068.png"
                            self.tickspeed -= 1
                            self.board.etat_champs[(x,y)] = True
                        elif self.board.champs_quete["2_"+str(x)+"_"+str(y)] == "assets/tilesets/x16_decorations/x16_decorations_058.png" :
                            self.web_helper.change_image("2_"+str(x)+"_"+str(y), "assets/tilesets/x16_decorations/x16_decorations_059.png")
                            self.board.champs_quete["2_"+str(x)+"_"+str(y)] = "assets/tilesets/x16_decorations/x16_decorations_059.png"
                            self.tickspeed -= 1
                        elif self.board.champs_quete["2_"+str(x)+"_"+str(y)] == "assets/tilesets/x16_decorations/x16_decorations_059.png" :
                            self.web_helper.change_image("2_"+str(x)+"_"+str(y), "assets/tilesets/x16_decorations/x16_decorations_065.png")
                            self.board.champs_quete["2_"+str(x)+"_"+str(y)] = "assets/tilesets/x16_decorations/x16_decorations_065.png"
                            self.tickspeed -= 1
                        elif self.board.champs_quete["2_"+str(x)+"_"+str(y)] == "assets/tilesets/x16_decorations/x16_decorations_065.png" :
                            self.web_helper.change_image("2_"+str(x)+"_"+str(y), "assets/tilesets/x16_decorations/x16_decorations_066.png")
                            self.board.champs_quete["2_"+str(x)+"_"+str(y)] = "assets/tilesets/x16_decorations/x16_decorations_066.png"
                            self.tickspeed -= 1
                            self.board.etat_champs[(x,y)] = True
                if (int(self.player.x//32+1), int(self.player.y//32+1)) in self.board.etat_champs :
                    self.web_manager.remove_class("quete_champs", "pressed")
                    if self.board.etat_champs[int(self.player.x//32+1), int(self.player.y//32+1)] == True :
                        if "KeyC" in keys :
                            if int(self.player.y//32+1)%2 == 0:
                                self.web_helper.change_image("2_"+str(int(self.player.x//32+1))+"_"+str(int(self.player.y//32+1)), "assets/tilesets/x16_decorations/x16_decorations_060.png")
                                self.tickspeed += 3
                                self.board.champs_quete["2_"+str(int(self.player.x//32+1))+"_"+str(int(self.player.y//32+1))] = "assets/tilesets/x16_decorations/x16_decorations_060.png"
                                self.board.etat_champs[(int(self.player.x//32+1), int(self.player.y//32+1))] = False
                                if "ble" not in self.place_inventaire:
                                    self.place_inventaire["ble"] = len(self.place_inventaire)
                                if "ble" not in self.inventaire:
                                    self.inventaire["ble"] = 0
                                if self.inventaire["ble"] < 64:
                                    self.inventaire["ble"] += 1
                                self.web_helper.change_text("indice"+str(self.place_inventaire["ble"]+1), str(self.inventaire["ble"]))
                                if self.inventaire["ble"] == 1:
                                    self.web_manager.insere("ble", "img", attr={'src':f'../assets/tilesets/x16_decorations/x16_decorations_074.png'}, style={"width": "5em"}, parent="div"+str(self.place_inventaire["ble"]+7))
                            else:
                                self.web_helper.change_image("2_"+str(int(self.player.x//32+1))+"_"+str(int(self.player.y//32+1)), "assets/tilesets/x16_decorations/x16_decorations_058.png")
                                self.tickspeed += 3
                                self.board.champs_quete["2_"+str(int(self.player.x//32+1))+"_"+str(int(self.player.y//32+1))] = "assets/tilesets/x16_decorations/x16_decorations_058.png"
                                self.board.etat_champs[(int(self.player.x//32+1), int(self.player.y//32+1))] = False
                                if "carotte" not in self.place_inventaire:
                                    self.place_inventaire["carotte"] = len(self.place_inventaire)
                                if "carotte" not in self.inventaire:
                                    self.inventaire["carotte"] = 0
                                if self.inventaire["carotte"] < 64:
                                    self.inventaire["carotte"] += 1
                                self.web_helper.change_text("indice"+str(self.place_inventaire["carotte"]+1), str(self.inventaire["carotte"]))
                                if self.inventaire["carotte"] == 1:
                                    self.web_manager.insere("carotte", "img", attr={'src':f'../assets/tilesets/x16_decorations/x16_decorations_073.png'}, style={"width": "5em"}, parent="div"+str(self.place_inventaire["carotte"]+7))
                else:
                    self.web_manager.add_class("quete_champs", "pressed")
                in_range_enemies = []
                player_range = self.player.weapon.range
                for enemy in self.enemies:
                    enemy.update(delta_time, self.player)
                    dst = sqrt((enemy.x - self.player.x) ** 2 + (enemy.y - self.player.y) ** 2)
                    if dst <= player_range:
                        in_range_enemies.append(enemy)
                if not self.player.is_dead():
                    player_movement = self.player.update(delta_time, keys, in_range_enemies)
                    if player_movement != [0, 0]:
                        mov_validate, new_interactable = self.collision_resolver.attempt_movement(self.player.get_boundaries(player_movement), player_movement)
                        if mov_validate:
                            self.player.render(player_movement)
                            # Actualiser les blocs rendus sur la carte et scroller si nécessaire
                            self.board.translate(web_helper.multiply_list(player_movement, -1))

            if new_interactable != -1:
                if new_interactable == None:
                    self.web_manager.change_text("action-bar", "")
                    if isinstance(self.interactable, Npc):
                        self.web_manager.remove_class(self.interactable.id, "highlight-blink")
                    self.interactable = None
                else:
                    self.interactable = new_interactable
                    self.web_manager.change_text("action-bar", "Appuyez sur E pour intéragir")
                    if isinstance(self.interactable, Npc):
                        self.web_manager.add_class(self.interactable.id, "highlight-blink")

    def stop(self):
        """
        Fonction a appeler pour fermer **correctement** le serveur
        """
        self.do_loop = False
        self.loop_thread.join()
        self.web_manager.stop()
        self.board.link.commit()
        self.board.link.close()

# On verifie que le programme n'est pas importe mais bien lance
if __name__ == "__main__":
    main()
