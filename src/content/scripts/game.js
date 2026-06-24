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
let player = null;

const HIT_FILTERS = "sepia(100%) brightness(0.9) contrast(0.9) hue-rotate(305deg) saturate(8)";
const HIT_DURATION = 500;

const FRONT = 0;
const RIGHT = 1;
const LEFT = 2;
const BACK = 3;

const IDLE = 0;
const WALK = 4
const ATTACK = 8;
const DIE = 12;

class AnimationProperties {
    constructor(name, spritesheetPath, size, availableAnimations, frames, durations) {
        this.name = name;

        this.spritesheetPath = spritesheetPath;
        this.spritesheet = new Image;
        this.spritesheet.src = spritesheetPath;
        this.size = size;

        this.availableAnimations = availableAnimations;
        // Liste, donne le nombre de frames pour chaque animation
        this.frames = frames;
        // Liste de listes, donne la durée de chaque frame pour chaque animation
        this.durations = durations
    }

    getFrames(animationIndex) {
        return this.frames[this.availableAnimations[animationIndex]];
    }

    getDurations(animationIndex) {
        return this.durations[this.availableAnimations[animationIndex]];
    }

    drawFrame(animationIndex, frame, x, y, dstSize) {
        while (!this.spritesheet.complete) {
            ;
        }
        charactersCanvasContext.drawImage(this.spritesheet,
            frame * this.size, this.availableAnimations[animationIndex] * this.size, this.size, this.size,
            x, y, dstSize, dstSize
        )
    }
}

animationMap.set("player", new AnimationProperties("player", "../assets/spritesheets/player.png", 32,
    [0, 1, 2, 3, 4, 5, 6, 7, 8,9 , 10, 11, 12],
    [6, 6, 6, 6, 6, 6, 6, 6, 4, 4, 4, 4, 4],
    [   [125, 125, 125, 125, 125, 125],
        [125, 125, 125, 125, 125, 125],
        [125, 125, 125, 125, 125, 125],
        [125, 125, 125, 125, 125, 125],
        [125, 125, 125, 125, 125, 125],
        [125, 125, 125, 125, 125, 125],
        [125, 125, 125, 125, 125, 125],
        [125, 125, 125, 125, 125, 125],
        [125, 125, 100, 125],
        [125, 125, 100, 125],
        [125, 125, 100, 125],
        [125, 125, 100, 125],
        [125, 125, 125, 200]]));

animationMap.set("slime", new AnimationProperties("slime", "../assets/spritesheets/slime.png", 64,
    [0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 2],
    [4, 8, 8],
    [[250, 200, 225, 250],
    [150, 150, 175, 75, 100, 100, 100, 100],
    [100, 50, 50, 50, 50, 50, 100, 100]]));

function addAnimation(name, path, size, availableAnimations, frameCounts, durations) {
    animationMap.set(name, new AnimationProperties(name, path, size, availableAnimations, frameCounts, durations));
}

function mapCoordinates(x, y, size) {
    let X = x - player.x + (window.innerWidth - player.size) / 2;
    let Y = y - player.y + (window.innerHeight - player.size) / 2;
    return [X, Y];
}

function drawRect(x1, y1, x2, y2) {
    let [X1, Y1] = mapCoordinates(x1, y1, 64);
    let [X2, Y2] = mapCoordinates(x2, y2, 64);
    charactersCanvasContext.strokeStyle = "red";
    charactersCanvasContext.lineWidth = 2;
    charactersCanvasContext.strokeRect(X1, Y1, X2 - X1, Y2 - Y1);
}

class Character {
    constructor(name, animationName, x, y, size) {
        this.name = name;

        this.animation = animationMap.get(animationName);
        this.lastAnimation = 0; // Utilisé que lors d'une attaque pour savoir vers quelle animation retourner après
        this.currentAnimation = 0;
        this.animationFrameIndex = 0;
        this.animationFrameCount = this.animation.getFrames(this.currentAnimation);
        this.animationDurations = this.animation.getDurations(this.currentAnimation);

        this.x = x;
        this.y = y;
        this.size = size;

        this.hit = false;
        this.hitLasted = 0;

        // Donne la durée passée sur la frame actuelle
        this.frameLasted = 0;
    }

    /**
     * Change l'indice de l'animation en cours
     * @param {number} animationIndex Indice de la nouvelle animation
     */
    changeAnimation(animationIndex) {
        if (8 <= this.currentAnimation && this.currentAnimation < 12 && this.animationFrameIndex + 1 < this.animationFrameCount) {
            // Si l'animation voulue n'est pas une attaque, elle viendre après l'attaque
            if (animationIndex < 8) {
                this.lastAnimation = animationIndex;
            }
            // On change seulement la direction de l'attaque
            this.currentAnimation = 8 + animationIndex % 4;
            return;
        }
        this.currentAnimation = animationIndex;
        this.animationFrameCount = this.animation.getFrames(this.currentAnimation);
        this.animationDurations = this.animation.getDurations(this.currentAnimation);
        this.animationFrameIndex = 0;
        this.frameLasted = 0;
    }

    tick(dT) {
        if (this.hit) {
            let newHitLasted = this.hitLasted + dT;
            if (newHitLasted > HIT_DURATION) {
                newHitLasted = 0;
                this.hit = false;
            }
            this.hitLasted = newHitLasted;
        }

        let newFrameLasted = this.frameLasted + dT;
        if (newFrameLasted > this.animationDurations[this.animationFrameIndex]) {
            newFrameLasted = 0;
            // Lorsque l'attaque est finie, on revient à l'animation précédente
            if (8 <= this.currentAnimation && this.currentAnimation < 12 && this.animationFrameIndex + 1 == this.animationFrameCount) {
                this.changeAnimation(this.lastAnimation);
            }
            // On ne veut pas passer à la prochaine frame si l'animation de mort est finie.
            if (!(this.currentAnimation == 12 && this.animationFrameIndex + 1 == this.animationFrameCount)) {
                this.animationFrameIndex += 1;
                this.animationFrameIndex %= this.animationFrameCount;
            }
        }
        this.frameLasted = newFrameLasted;

        if (this.hit) {
            charactersCanvasContext.filter = HIT_FILTERS;
        }
        let x = this.x;
        let y = this.y;
        if (this.name !== "player") {
            x = x - player.x + (window.innerWidth - player.size) / 2
            y = y - player.y + (window.innerHeight - player.size) / 2
        }
        else {
            x = (window.innerWidth  - this.size) / 2
            y = (window.innerHeight - this.size) / 2
        }
        this.animation.drawFrame(this.currentAnimation, this.animationFrameIndex, x, y, this.size);
        if (this.hit) {
            charactersCanvasContext.filter = "none";
        }
    }
}

function add_character(name, animation, x, y, size) {
    remove_character(name);
    let character = new Character(name, animation, x, y, size);
    if (name === "player") {
        player = character;
    }
    characterMap.set(name, character);

    // On ajoute le personnage a la liste triée des personnages
    characterSortedList.push(character);
    characterSortedList.sort((a,b) => a.y - b.y);
}

function remove_character(name) {
    characterSortedList = characterSortedList.filter((c) => c.name !== name);
    characterMap.delete(name);
}

function change_render(characterName, animation) {
    let character = characterMap.get(characterName);

    if (character.animationIndex != animation) {
        character.changeAnimation(animation);
    }
}

function move(characterName, x ,y) {
    let character = characterMap.get(characterName);

    character.x = x;
    if (character.y != y) {
        sorted = false;
        character.y = y;
    }
}

function hit_character(name) {
    let character = characterMap.get(name);
    character.hit = true;
}

function updateRender(timestamp) {
    /*if (animationMap.size == 0 || !animationMap.values().next().value.spritesheet.complete) {
        requestAnimationFrame(updateRender);
    }*/

    charactersCanvasContext.clearRect(0, 0, charactersCanvas.width, charactersCanvas.height);

    deltaTime = timestamp - lastUpdate;

    if (!sorted) {
        characterSortedList.sort((a,b) => a.y - b.y);
    }

    characterSortedList.forEach(character => {
        character.tick(deltaTime);
    });

    lastUpdate = timestamp;

    requestAnimationFrame(updateRender);
}
