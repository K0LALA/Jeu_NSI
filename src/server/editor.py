import os # remove, listdir, path.isfile
import time # time
import threading # Threading
import sqlite3

import wsinter
import web_helper

import graphics.board
from inputs.keyboard import Keyboard
from inputs.mouse import Mouse

editor = None

def main():
    global editor
    
    try:
        lock = open("launched", "x")
        lock.close()
    except FileExistsError:
        raise FileExistsError("Une instance du serveur est deja lancee")

    editor = Editor(start_page = "editor.html")
    
def stop():
    global editor
    editor.stop()
    
    os.remove("launched")
    exit(0)
    
class Editor:
    def __init__(self, start_page: str):
        self.web_manager = wsinter.Inter("content/pages/" + start_page)
        # On utilise notre propre initialisation pour la souris
        self.web_manager.demarre(clavier=True, souris=False)
        
        self.web_helper = web_helper.Helper(self.web_manager)
        
        self.board: graphics.board.EditorBoard = None
        self.link = sqlite3.connect("content/data/worlds/worlds.db")
        self.base = self.link.cursor()
        
        self.add_elements()

        self.keyboard_manager = Keyboard(self.web_manager)
        self.mouse_manager = Mouse(self.web_manager)
        
        self.loop_thread = threading.Thread(target=self.loop)
    
    def add_elements(self):
        # On ajoute tous les mondes possibles
        self.base.execute("SELECT name FROM worlds;")
        worlds = self.base.fetchall()
        if len(worlds) == 1:
            self.world_changed(None, worlds[0][0])
        for world in worlds:
            self.web_manager.insere(world[0], "option", attr={"value":world[0]}, parent="world")
            self.web_manager.change_text(world[0], world[0])
            
        # On ajoute toutes les tilesets possibles
        for file in os.listdir("content/assets/tilesets"):
            if os.path.isfile("content/assets/tilesets" + file):
                continue
            self.web_manager.insere(file, "option", attr={"value":file}, parent="tileset-choice")
            self.web_manager.change_text(file, file)                
        
        # On crée des gestionnaires pour les divers evenements
        self.web_manager.gestionnaire("world_changed", self.world_changed)
    
    def world_changed(self, _, o: str):
        self.world = o
        
        # On charge le plateau
        self.board = graphics.board.EditorBoard(self.web_helper, self.world)
        
        if not self.loop_thread.is_alive():
            self.loop_thread.start()
        
        self.web_manager.gestionnaire("layer_changed", self.board.layer_changed)
        self.web_manager.gestionnaire("create_layer", self.board.create_layer)
        self.web_manager.gestionnaire("delete_layer", self.board.delete_layer)
        self.web_manager.gestionnaire("tile_changed", self.board.tile_changed)
        self.web_manager.gestionnaire("tool_changed", self.board.tool_changed)
            
    def loop(self):
        self.do_loop = True
        last_loop_time = 0
        delta_save_time = 0
        
        while self.board == None:
            time.sleep(0.5)
        

        while self.do_loop:
            delta_time = time.time() - last_loop_time - 0.01
            delta_save_time += delta_time + 0.01
            if delta_time < 0:
                time.sleep(-delta_time / 4)
                continue
            
            if delta_save_time > 15 and self.board != None and self.board.link != None:
                self.board.link.commit()
                delta_save_time = 0

            delta_time += 0.01
            
            window_size = self.web_manager.get_window_size_if_changed()
            
            if window_size != None:
                self.board.window_size_changed()
            
            keys = self.keyboard_manager.get_keys()
            buttons = self.mouse_manager.get_buttons()

            # On bouge la carte
            move = [0, 0]
            if "ArrowDown" in keys:
                move[1] -= 1
            if "ArrowLeft" in keys:
                move[0] += 1
            if "ArrowUp" in keys:
                move[1] += 1
            if "ArrowRight" in keys:
                move[0] -= 1
            if move != [0, 0]:
                self.board.translate_direction(move)
            
            if buttons[0]['L'] or buttons[0]['R']:
                button = 'L' if buttons[0]['L'] else 'R'
                self.board.action(button, buttons[1])
            
            last_loop_time = time.time()

        if self.board.link != None and not self.board.commit:
            self.board.link.commit()
            
    def stop(self):
        self.do_loop = False
        if self.loop_thread.is_alive():
            self.loop_thread.join()
        self.web_manager.stop()
        if self.board != None and self.board.link != None:
            self.board.link.commit()
            self.board.link.close()
        
if __name__ == "__main__":
    main()
