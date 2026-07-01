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
window.addEventListener("resize", (_) => {
    charactersCanvas.width = window.innerWidth;
    charactersCanvas.height = window.innerHeight;
    charactersCanvasContext.imageSmoothingEnabled = false;
});
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
    constructor(name, spritesheetPath, size, animationMapping) {
        this.name = name;

        this.spritesheetPath = spritesheetPath;
        this.spritesheet = new Image;
        this.spritesheet.src = spritesheetPath;
        this.size = size;

        // Object{animationName -> Array[position: number, repeat: boolean, frameCount: Array, durations: Array]}
        this.animationMapping = animationMapping;
    }

    testIfAnimationExists(animation) {
        if (!this.animationMapping.hasOwnProperty(animation)) {
            console.error("AnimationMapping has not such property:", this.name, animation);
            return false;
        }
        return true;
    }

    isRepeating(animation) {
        if (!this.testIfAnimationExists(animation)) return null;
        return this.animationMapping[animation].at(1);
    }

    getFrames(animation) {
        if (!this.testIfAnimationExists(animation)) return null;
        return this.animationMapping[animation].at(2);
    }

    getDurations(animation) {
        if (!this.testIfAnimationExists(animation)) return null;
        return this.animationMapping[animation].at(3);
    }

    drawFrame(animation, frame, x, y, dstSize) {
        if (!this.testIfAnimationExists(animation)) return null;
        while (!this.spritesheet.complete) {
            ;
        }
        charactersCanvasContext.drawImage(this.spritesheet,
            frame * this.size, this.animationMapping[animation].at(0) * this.size, this.size, this.size,
            x, y, dstSize, dstSize
        )
    }
}

/*animationMap.set("player", new AnimationProperties("player", "../assets/spritesheets/player.png", 32,
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
    [100, 50, 50, 50, 50, 50, 100, 100]]));*/

function addAnimation(name, path, size, animationMapping) {
    animationMap.set(name, new AnimationProperties(name, path, size, animationMapping));
}

class Character {
    constructor(name, animationName, startingAnimation, x, y, size) {
        this.name = name;

        this.ANIMATION = animationMap.get(animationName);
        
        this.currentAnimation = startingAnimation;
        this.animationPrefix = this.currentAnimation.slice(0, this.currentAnimation.indexOf(';'));
        this.nextAnimation = ""; // Utilisé lorsqu'une animation ne peut pas etre interrompue pour savoir laquelle vient après

        this.animationFrameIndex = 0;
        this.doRepeat = this.ANIMATION.isRepeating(this.currentAnimation);
        this.animationFrameCount = this.ANIMATION.getFrames(this.currentAnimation);
        this.animationDurations = this.ANIMATION.getDurations(this.currentAnimation);

        this.x = x;
        this.y = y;
        this.size = size;

        this.hit = false;
        this.hitLasted = 0;

        // Donne la durée passée sur la frame actuelle
        this.frameLasted = 0;
    }

    /**
     * Change l'animation en cours
     * @param {string} newAnimation Nouvelle animation
     */
    changeAnimation(newAnimation) {
        if (this.currentAnimation === "die;") {
            return;
        }
        // Si l'animation ne se répète pas, elle ne peut pas être interrompue (c.f. characters/README.md)
        // Si l'action est la même on change de direction, sinon on attend que l'animation actuelle soit finie
        if (!this.doRepeat && this.animationFrameIndex + 1 < this.animationFrameCount) {
            // On change seulement la direction de l'animation
            if (newAnimation.startsWith(this.animationPrefix)) {
                this.currentAnimation = newAnimation;
            }
            else {
                this.nextAnimation = newAnimation;
            }
            return;
        }
        this.animationPrefix = newAnimation.slice(0, newAnimation.indexOf(';'));
        this.currentAnimation = newAnimation;
        this.doRepeat = this.ANIMATION.isRepeating(this.currentAnimation);
        this.animationFrameCount = this.ANIMATION.getFrames(this.currentAnimation);
        this.animationDurations = this.ANIMATION.getDurations(this.currentAnimation);
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
            // Si l'attaque ne se répète pas, on revient à la précédente lorsqu'elle est finie
            if (!this.doRepeat && this.animationFrameIndex + 1 == this.animationFrameCount) {
                this.changeAnimation(this.nextAnimation);
            }
            // On ne veut pas passer à la prochaine frame si l'animation de mort est finie.
            if (this.currentAnimation === "die;" && this.animationFrameIndex + 1 == this.animationFrameCount) {
                if (this.name !== "player") {
                    remove_character(this.name);
                }
            }
            else {
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
        this.ANIMATION.drawFrame(this.currentAnimation, this.animationFrameIndex, Math.round(x), Math.round(y), this.size);
        if (this.hit) {
            charactersCanvasContext.filter = "none";
        }
    }
}

function add_character(name, animation, startAnimation, x, y, size) {
    remove_character(name);
    let character = new Character(name, animation, startAnimation, x, y, size);
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
    
    if (character.currentAnimation != animation) {
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
