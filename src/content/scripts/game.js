// L'objectif de ce script est de gérer l'affichage des personnages
// En effet l'utilisation de GIF pour chacun des personnages est laborieux
// D'une part pour l'export, il faut sélectionner les frames voulues, leur mettre une certaine durée puis exporter en GIF pour chaque animation
// D'autre part pour le rendu, les GIFs demandent beaucoup de ressources au processeur
// Ce script a donc pour but de simplifier ces 2 processus en utilisant un canvas commun à tous les personnages
// De plus, avec un tel fonctionnement, il devient alors possible d'avoir les personnages qui se chevauchent mieux selon leur position par rappport aux autres

// A chaque frame, on fait donc le rendu de tous les personnages
// Les personnages sont stockés dans une liste triée dans l'ordre croissant en fonction de leur position Y
// Les premiers personnages de la liste sont rendus au second plan
// Pour chacun des personnages, on stocke donc l'animation actuelle, l'indice de la frame dans l'animation et la position
let charactersCanvas = document.getElementById("canvas-characters");
charactersCanvas.width = window.innerWidth;
charactersCanvas.height = window.innerHeight;
let charactersCanvasContext = charactersCanvas.getContext("2d");
charactersCanvasContext.imageSmoothingEnabled = false;
let animationMap = new Map();
let characterMap = new Map();
// Liste des personnages triées par rapport à leur position en Y, de la plus grande à la plus petite (BACK: +Y, FRONT: -Y)
let characterSortedList = new Array();
sorted = true;
let lastUpdate = document.timeline.currentTime;

class Animation {
    constructor(name, spritesheetPath, size, frames, durations) {
        this.name = name;

        this.spritesheetPath = spritesheetPath;
        this.spritesheet = new Image;
        this.spritesheet.src = spritesheetPath;
        this.size = size;

        // Liste, donne le nombre de frames pour chaque animation
        this.frames = frames;
        // Liste de listes, donne la durée de chaque frame pour chaque animation
        this.durations = durations
    }

    getFrames(animationIndex) {
        return this.frames[animationIndex];
    }

    getDurations(animationIndex) {
        return this.durations[animationIndex];
    }

    drawFrame(animationIndex, frame, x, y, dstSize) {
        while (!this.spritesheet.complete) {
            ;
        }
        charactersCanvasContext.drawImage(this.spritesheet,
            frame * this.size, animationIndex * this.size, this.size, this.size,
            x, y, dstSize, dstSize
        )
    }
}

animationMap.set("player", new Animation("player", "../assets/spritesheets/player.png", 32,
    [6, 6, 6, 6, 6, 6, 6, 6, 4, 4, 4, 4, 4],
    [   [150, 150, 150, 150, 150, 150],
        [150, 150, 150, 150, 150, 150],
        [150, 150, 150, 150, 150, 150],
        [150, 150, 150, 150, 150, 150],
        [150, 150, 150, 150, 150, 150],
        [150, 150, 150, 150, 150, 150],
        [150, 150, 150, 150, 150, 150],
        [150, 150, 150, 150, 150, 150],
        [150, 150, 100, 150],
        [150, 150, 100, 150],
        [150, 150, 100, 150],
        [150, 150, 100, 150],
        [150, 150, 150, 200]]));

class Character {
    constructor(name, animationName, x, y, size) {
        this.name = name;

        this.animation = animationMap.get(animationName);
        this.currentAnimation = 0;
        this.animationFrameIndex = 0;
        this.animationFrameCount = this.animation.getFrames(this.currentAnimation);
        this.animationDurations = this.animation.getDurations(this.currentAnimation);

        this.x = x;
        this.y = y;
        this.size = size;

        // Donne la durée passée sur la frame actuelle
        this.lasted = 0;
    }

    /**
     * Change l'indice de l'animation en cours
     * @param {number} animationIndex Indice de la nouvelle animation
     */
    changeAnimation(animationIndex) {
        this.currentAnimation = animationIndex;
        this.animationFrameCount = this.animation.getFrames(this.currentAnimation);
        this.animationDurations = this.animation.getDurations(this.currentAnimation);
        this.animationFrameIndex = 0;
        this.lasted = 0;
    }

    tick(dT) {
        let new_lasted = this.lasted + dT;
        if (new_lasted > this.animationDurations[this.animationFrameIndex]) {
            new_lasted = 0;
            this.animationFrameIndex += 1;
            this.animationFrameIndex %= this.animationFrameCount;
        }
        this.lasted = new_lasted;

        this.animation.drawFrame(this.currentAnimation, this.animationFrameIndex, this.x, this.y, this.size);
    }
}

// TODO: Ajouter dans wsinter à la place pour éviter les injecte
function add_character(name, spritesheetPath, x, y, size) {
    let character = new Character(name, spritesheetPath, x, y, size);
    characterMap.set(name, character);

    // On ajoute le personnage a la liste triée des personnages
    characterSortedList.push(character);
    characterSortedList.sort((a,b) => b.y - a.y);
}

function change_render(characterName, animation, x, y) {
    let character = characterMap.get(characterName);

    character.x = x;
    if (character.y != y) {
        sorted = false;        
        character.y = y;
    }

    if (character.animationIndex != animation) {
        character.changeAnimation(animation);
    }
}

function updateRender(timestamp) {
    if (!animationMap.values().next().value.spritesheet.complete) {
        requestAnimationFrame(updateRender);
    }

    charactersCanvasContext.clearRect(0, 0, charactersCanvas.width, charactersCanvas.height);

    deltaTime = timestamp - lastUpdate;

    if (!sorted) {
        characterSortedList.sort((a,b) => b.y - a.y);
    }

    characterSortedList.forEach(character => {
        character.tick(deltaTime);
    });

    lastUpdate = timestamp;

    requestAnimationFrame(updateRender);
}
