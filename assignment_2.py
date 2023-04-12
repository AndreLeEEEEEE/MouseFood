import pygame as pg
import numpy as np
from scipy.spatial import distance
import random
import os
import time
from enum import Enum

# Initialize pygame.
pg.init()

# Get the current path of the python file. Used to load a font resource.
ABS_PATH = os.path.dirname(os.path.realpath(__file__))

# Window width and height
WINDOW_WIDTH = 600
WINDOW_HEIGHT = 700

# How many tiles should the grid have horizontally and vertically?
# CURRENTLY ALL GRIDS MUST BE SQUARE
GAME_GRID_WIDTH = 10
GAME_GRID_HEIGHT = GAME_GRID_WIDTH

# Total number of spaces 
NUM_SPACES = GAME_GRID_WIDTH * GAME_GRID_HEIGHT

# Not currently used.
SMELL_PROPAGATION_DISTANCE = GAME_GRID_WIDTH

# How much energy is spent moving from tile to tile
DEFAULT_TERRAIN_DIFFICULTY = 1

# Should food smell stack, or take the greatest value?
# Glitches can occur if this is turned off
SCENT_STACKING = True

# Does a round's score go down to zero if the player dies?
DEATH_PENALTY = True

# Self explanatory
BACKGROUND_COLOR = pg.Color("#505050")
PAUSED_BACKGROUND_COLOR = pg.Color("#303030")

# Number of frames to draw per second.
FRAMES_PER_SECOND = 60

# Used to determine how many frames are skipped.
# Helps when you want the gamelogic to move faster than
# Your system can draw it.
SKIP_FRAMES = 0

# How much energy does the mouse get from food?
ENERGY_PER_FOOD = 20

# How much food needs to be found before a round ends?
FOOD_PER_ROUND = 20

# What is the maximum amount of energy that a player can have?
MAX_ENERGY = 100

# Maximum number of game states that can be saved per round
MAX_SAVED_GAME_STATES = MAX_ENERGY

# The number of food pieces that will spawn each time there is no food
# on the grid.
MAX_NUM_FOOD_ON_GRID = 2

# A reference enumeration for the values associated with
# the cardinal movements.
class Direction(Enum):
    # 0 -> North (UP)
    # 1 -> South (DOWN)
    # 2 -> WEST (LEFT)
    # 3 -> EAST (RIGHT)
    NORTH = 0
    UP = 0
    
    SOUTH = 1
    DOWN = 1
    
    WEST = 2
    LEFT = 2

    EAST = 3
    RIGHT = 3

# A class that describes a occupied tile on the grid.
class GridSpace:
    def __init__(self,x,y):
        self.type = None
        self.difficulty = DEFAULT_TERRAIN_DIFFICULTY
        self.x = x
        self.y = y
        self.color = pg.Color("#000000")
    # Set a tile to be type 'player'
    def setPlayer(self):
        self.color = pg.Color("#0000FF")
        self.type = "Player"

    # Set a tile to be type 'food'    
    def setFood(self):
        self.color = pg.Color("#FF0000")
        self.type = "Food"

# A class that allows for the saving and restoring of the game.
class GameState():
    def __init__(self,game_grid):
        self.player_loc_x = game_grid.player.tile.x
        self.player_loc_y = game_grid.player.tile.y
        self.player_energy = game_grid.player.energy
        self.player_food_eaten = game_grid.player.food_eaten
        self.player_score = game_grid.player.score
        
        self.foods_loc = []
        for tile in game_grid.occupied_spaces:
            if tile.type == "Food":
                self.foods_loc.append([tile.x,tile.y])

    # Restore a player object from the game state
    def restorePlayer(self):
        player = Player(self.player_loc_x, self.player_loc_y)
        player.energy = self.player_energy
        player.food_eaten = self.player_food_eaten
        player.score = self.player_score
        return player

# A class that controls the logic and graphics of the game.
class GameManager():
    def __init__(self,width,height):
        self.game_grid = GameGrid(height, width)
        self.round = 0
        self.paused = 0
        self.game_states = []
        self.game_grid.addFood()
        self.round_scores = []

    # Proceed one tick in the game logic.
    def logicTick(self):
        # Add food if there is none on the grid
        if self.game_grid.occupied_spaces == []:
            for i in range(MAX_NUM_FOOD_ON_GRID):
                self.game_grid.addFood()

        self.game_grid.calcSmellMatrix()
        self.game_grid.calcPlayerSense()
        movement = smart_mouse(self.game_grid.player.smell_matrix)
        self.game_grid.movePlayer(movement)
        self.checkEndStates()
        self.saveGameState()

    # Draw the current gamestate to the screen
    def draw(self,game_window):
        if self.paused:
            game_window.fill(PAUSED_BACKGROUND_COLOR)
        else:
            game_window.fill(BACKGROUND_COLOR)

        self.game_grid.draw(game_window)
        labels_y_start = self.game_grid.total_grid_x + self.game_grid.grid_padding
        game_window.blit(font.render(f"SCORE:            {self.game_grid.player.score}", 0, (255, 0, 0)), (10, labels_y_start))
        game_window.blit(font.render(f"ENERGY:          {self.game_grid.player.energy}", 0, (255, 0, 0)), (10, labels_y_start+50))
        game_window.blit(font.render(f"FOOD_FOUND:  {self.game_grid.player.food_eaten}", 0, (255, 0, 0)), (10, labels_y_start+100))        
        game_window.blit(font.render(f"Round: {self.round}", 0, (255, 0, 0)), (10, 0))        

        pg.display.flip()        

    # Check if something happened to end the round.
    # If statements are separated in case you wanted to modify the behavior to 
    def checkEndStates(self):
        # If the player eats enough food to end the round
        if self.game_grid.player.food_eaten >= FOOD_PER_ROUND:
            self.endRound()
            return
        # If the player died (Starved)
        if not self.game_grid.player.alive:
            if DEATH_PENALTY:
                self.game_grid.player.score = 0
            self.endRound()
            return

    # Ed the round and start a new one.
    def endRound(self):
            self.round_scores.append(self.game_grid.player.score)
            self.game_grid.reset()
            self.round += 1
            # DEBUG
            #   self.printScoreStats()
            # /DEBUG
            self.reset()

    # Print score related statistics.
    def printScoreStats(self):
        print(f"There have been {len(self.round_scores)} round(s).")
        print(f"The highest possible score is {MAX_ENERGY*FOOD_PER_ROUND}")
        print(f"The high score of all rounds is {max(self.round_scores)}")
        print(f"The worst of all rounds is {min(self.round_scores)}")
        print(f"The average of all rounds is {sum(self.round_scores)/len(self.round_scores)}")
        print()

    # Reset self to prepare for the next round
    def reset(self):
        self.game_states = []

    # Save the current game state, and add it to the game state array.
    def saveGameState(self):
        if len(self.game_states) >= MAX_SAVED_GAME_STATES:
            self.game_states = self.game_states[1:]
        self.game_states.append(GameState(self.game_grid))

    # Restore a game state from a GameState object
    def restoreGameState(self,game_state):
        self.game_grid.reset()
        self.game_grid.player = game_state.restorePlayer()
        for food in game_state.foods_loc:
            self.game_grid.addFood(food[0], food[1])

    # Rewind a given number of game states.
    def rewindGameState(self,num_to_rewind):
        if len(self.game_states) <= 1:
            return
        if num_to_rewind >= len(self.game_states):
            num_to_rewind = len(self.game_states) - 1

        self.game_states = self.game_states[:-num_to_rewind]
        self.restoreGameState(self.game_states[-1])

# A class managing player actions
class Player:
    def __init__(self,x=0,y=0):
        self.tile = GridSpace(x,y)
        self.tile.setPlayer()
        self.food_eaten = 0
        self.max_energy = MAX_ENERGY
        self.energy = self.max_energy
        self.alive = True
        self.smell_matrix = np.zeros((3,3))
        self.score = 0
    
    # Move to a location without using energy
    def teleport(self,x,y):
        self.tile.x = x
        self.tile.y = y

    # Move one space in a given direction. DIfficulty will be used later
    # to increase or decrease energy usage when moving onto a square.,
    def move(self,direction,difficulty):
        if self.alive:
            if direction == 0:
                if self.tile.y > 0:
                    self.tile.y -= 1
            elif direction == 1:
                if self.tile.y < GAME_GRID_HEIGHT - 1:
                    self.tile.y += 1
            elif direction == 2:
                if self.tile.x > 0:
                    self.tile.x -= 1
            elif direction == 3:
                if self.tile.x < GAME_GRID_WIDTH - 1:
                    self.tile.x += 1        
            
            self.useEnergy(difficulty)
        return self.tile.x, self.tile.y

    # Eat a food
    def eatFood(self):
        self.food_eaten += 1
        self.score += self.energy
        self.energy += ENERGY_PER_FOOD
        if self.energy > self.max_energy:
            self.energy = self.max_energy
            
    # Use a given amount of energy 
    def useEnergy(self,amnt):
        self.energy -= amnt
        if self.energy < 0:
            self.die()
    
    # Turn the player from the alive state to the not-alive state
    def die(self):
        self.alive = False
        self.tile.color = pg.Color("#00005F")

    def printStats(self):
        print(f"FOOD EATEN: {self.food_eaten}")

# Primary game grid actions
class GameGrid:
    def __init__(self,width,height):
        self.width = width
        self.height = height

        score = 0
        self.smell_grid = []
        self.occupied_grid = []
        self.occupied_spaces = []

        self.reset()
        self.default_color = pg.Color("#FFFFFF")
        self.line_color = pg.Color("#010101")
        self.player = Player()
        self.padding = 2
        self.square_size = int(WINDOW_WIDTH/GAME_GRID_WIDTH*0.8)
        self.grid_padding = self.calcGridPadding()
                
    # Used to determine the size of the grid on screen.
    def calcGridPadding(self):
        self.total_grid_x = self.width*self.padding + self.width*self.square_size
        self.grid_padding = int((WINDOW_WIDTH - self.total_grid_x)/2)
        return self.grid_padding
    
    # Calculate how much food smell is on the current grid.
    def calcSmellMatrix(self):
        self.smell_grid = np.zeros((self.width, self.height))
        for tile in self.occupied_spaces:
            self.smell_grid[tile.x][tile.y] = 1
            for i in range(self.height):
                for j in range(self.width):
                    dist = distance.euclidean((i,j),(tile.x,tile.y)) + 1
                    dist = 1/dist
                    if SCENT_STACKING == False:
                        if self.smell_grid[j][i] < round(dist,5):
                            self.smell_grid[j][i] = round(dist,5)
                    else:
                        if j == tile.x and i == tile.y:
                            self.smell_grid[j][i] = round(dist,5)
                        else:
                            self.smell_grid[j][i] += round(dist,5)

    # Calculate what the player can sense from the current smell matrix.
    def calcPlayerSense(self):
        self.player.smell_matrix = np.zeros((3,3))
        padded_grid = np.pad(self.smell_grid,pad_width=1)
        x = self.player.tile.x
        y = self.player.tile.y
        self.player.smell_matrix = np.array(padded_grid[y:y+3,x:x+3])

    # Get a tile by it's coordinates. If no tile matches, return None
    def getTile(self,x,y):
        if not self.checkValidTile(x,y):
            return None
        for tile in self.occupied_spaces:
            if tile.x == x and tile.y == y:
                return tile
        return None

    # Draw the grid without anything else.
    def drawGrid(self,surface):
        total_x = self.width*self.padding + self.width*self.square_size
        total_y = self.height*self.padding + self.height*self.square_size
        
        grid_pos_x = self.padding + self.grid_padding
        for i in range(self.height + 1):
            pg.draw.rect(
                        surface,
                        self.line_color,
                        pg.Rect(
                            grid_pos_x,
                            self.padding + self.grid_padding, 
                            self.padding, 
                            total_y)
                    )
            grid_pos_x += self.square_size + self.padding

        grid_pos_y = self.padding + self.grid_padding
        for i in range(self.width + 1):
            pg.draw.rect(
                        surface,
                        self.line_color,
                        pg.Rect(
                            self.padding + self.grid_padding,
                            grid_pos_y, 
                            total_x,
                            self.padding
                            )
                    )
            grid_pos_y += self.square_size + self.padding

    # Calculate a XY location for a given tile location
    def calcTileLocation(self,tile):
        x = tile.x * self.padding + tile.x * self.square_size + self.grid_padding
        y = tile.y * self.padding + tile.y * self.square_size + self.grid_padding
        x += self.padding*2
        y += self.padding*2
        
        return x, y

    # Draw a tile in the grid
    def drawTile(self,surface,tile):
        x, y = self.calcTileLocation(tile)
        pg.draw.rect(
            surface,
            tile.color,
            pg.Rect(
                x, 
                y, 
                self.square_size, 
                self.square_size)
        )

    # Draw the entire game grid
    def draw(self,surface):
        total_x = self.width*self.padding + self.width*self.square_size
        total_y = self.height*self.padding + self.height*self.square_size
        pg.draw.rect(
                    surface,
                    self.default_color,
                    pg.Rect(
                        self.padding + self.grid_padding,
                        self.padding + self.grid_padding, 
                        total_x, 
                        total_y)
                )
        
        for tile in self.occupied_spaces:
            self.drawTile(surface,tile)
        
        self.drawTile(surface,self.player.tile)
        

        self.drawGrid(surface)

    # Add a tile to the game grid.
    def addTile(self,tile):
        self.occupied_spaces.append(tile)
        self.occupied_grid[tile.x][tile.y] = 1

    # Reset the game grid
    def reset(self):
        self.smell_grid = np.zeros((self.width, self.height))
        self.occupied_grid = np.zeros((self.width, self.height),dtype="int")
        self.occupied_spaces = []
        self.player = Player()
    
    # Get a random valid X coordinate.
    def randGridX(self):
        return random.randint(0,GAME_GRID_WIDTH-1)

    # Get a random valid Y coordinate.
    def randGridY(self):
        return random.randint(0,GAME_GRID_HEIGHT-1)


    # Get a random valid XY coordinate set.
    def randGridSpace(self):
        return self.randGridX(), self.randGridY()

    # Efficiently get a random XY pair that isn't already used. 
    def randEmptySpace(self):
        if len(self.occupied_spaces) < NUM_SPACES*0.5:
            found = False
            while found == False:
                x,y = self.randGridSpace()
                if self.occupied_grid[x][y] == 0:
                    found = True
            return x,y 
        else:
            empty_left = NUM_SPACES-len(self.occupied_spaces)
            choice = random.randint(0,empty_left)
            count = 0
            for i in range(self.height):
                for j in range(self.width):
                    if self.occupied_grid[i][j] == 0:
                        if count >= choice:
                            return i,j
                        count += 1
            for i in range(self.height):
                for j in range(self.width):
                    if self.occupied_grid[i][j] == 0:
                        if count >= choice:
                            return i,j
                        count += 1
            print("ERROR: No spaces available")
            exit(9)

    # Create a random tile, or one with the XY coordinate that is given.
    def genTile(self,x,y):
        if NUM_SPACES <= len(self.occupied_spaces):
            return None
        orig_x = x
        orig_y = y
        check_count = 0
        if orig_x < 0 or orig_x > GAME_GRID_WIDTH or \
            orig_y < 0 or orig_y > GAME_GRID_HEIGHT:
                x,y = self.randEmptySpace()
        return GridSpace(x,y)

    # Check to make sure a given XY set is 
    def checkValidTile(self,x,y):
        if x >= 0 and y >= 0:
            if x < GAME_GRID_WIDTH and y < GAME_GRID_HEIGHT:
                return True
        return False

    # Check to see if a given XY set is already occupied by a tile.
    def checkOccupied(self,x,y):
        if self.checkValidTile(x,y):
            if self.occupied_grid[x][y] == 1:
                return True        
        return False

    # Remove a tile at a given XY set, if one exists.
    def removeTile(self,x,y):
        tile_type = None
        if self.checkOccupied(x,y):
            self.occupied_grid[x][y] = 0
            for tile in self.occupied_spaces:
                if tile.x == x and tile.y == y:
                    tile_type = tile.type
                    self.occupied_spaces.remove(tile)
        return tile_type 

    # Move the player in a direction.
    def movePlayer(self,direction):
        # Dir is a number between 0 and 3:
        # 0 -> North (UP)
        # 1 -> South (DOWN)
        # 2 -> WEST (LEFT)
        # 3 -> EAST (RIGHT)

        x,y = self.player.move(direction,1)
        
        removed_tile_type = self.removeTile(x,y)
        if removed_tile_type == "Food":
            self.player.eatFood()
            self.calcSmellMatrix()

    # Add a player to the grid.
    def addPlayer(self,x=-1,y=-1):
        temp_tile = self.genTile(x,y)
        if temp_tile != None:
            temp_tile.setPlayer()
            self.addTile(temp_tile)

    # add a piece of food to the grid
    def addFood(self,x=-1,y=-1):
        temp_tile = self.genTile(x,y)
        if temp_tile != None:
            temp_tile.setFood()
            self.addTile(temp_tile)
        self.calcSmellMatrix()

    # Check if there is food at the XY set provided
    def checkForFood(self,x,y):
        if self.checkOccupied(x,y):
            tile = self.getTile(x,y)
            if tile is not None and tile.type == "Food":
                return True
        return False

    # Check to see if there is food next to the player, and
    # return the set of directions that lead to food.
    def isPlayerNext2Food(self):
        x = self.player.tile.x
        y = self.player.tile.y
        food_tiles = []

        if self.checkForFood(x-1,y):
            food_tiles.append(Direction.WEST.value)
        if self.checkForFood(x+1,y):
            food_tiles.append(Direction.EAST.value)
        if self.checkForFood(x,y-1):
            food_tiles.append(Direction.NORTH.value)
        if self.checkForFood(x,y+1):
            food_tiles.append(Direction.SOUTH.value)

        if food_tiles != []:
            return food_tiles
        else:
            return None

    # Print a list of all occupied tiles.
    def print_occupied_tiles(self):
        print(f"PLAYER AT: [{self.player.tile.x}, {self.player.tile.y}]")
        for tile in self.occupied_spaces:
            if tile.type == "Food":
                print(f"FOOD AT: [{tile.x}, {tile.y}]")

# All simple mouse does is pick a random direction, and moves there.
# Quite senseless, if you ask me.
def simple_mouse():
    return random.choice(range(0,4))



# Decides wether or not to use the corners of the player sensory matrix
# when selecting a movement path. In its current state, the mouse can get
# stuck in a rut when this is true when multiple pieces of food are in play. 
# You can try to improve it, if you'd like.

# Do you think your RL model will make better use of the corners, or
# do you think it will rely on the cardinal directions that it can use
# for movement?

USE_DIAGONAL_SCENT = False


# The smart mouse uses its nose to find food. It does this by checking
# which path has the greatest amount of food smells, and going in that
# direction. 

def smart_mouse(scent_matrix):
    # If there are no scents, just pick a random direction.
    if not np.any(scent_matrix):
        return simple_mouse()

    
    if USE_DIAGONAL_SCENT:
        # Sum the top, bottom, and side rows/columns
        north = np.sum(scent_matrix,axis=1)[0]
        south = np.sum(scent_matrix,axis=1)[2]
        west = np.sum(scent_matrix,axis=0)[0]
        east = np.sum(scent_matrix,axis=0)[2]
    else:
        # Get the values of the top center, bottom center, and side centers. 
        north = scent_matrix[0][1]
        south = scent_matrix[2][1]
        west = scent_matrix[1][0]
        east = scent_matrix[1][2]


    movement_array = [north,south,west,east]

    # Check if a food can be reached in a single move
    nearby_food = gm.game_grid.isPlayerNext2Food()

    # Move to a nearby piece of food, if one exists.
    if nearby_food != None:
        move_choice = random.choice(nearby_food)
        return move_choice

    # Get the maximum value, or values
    indexes = [i for i, x in enumerate(movement_array) if x == max(movement_array)]

    # Make a random choice from all the best options
    move_choice = random.choice(indexes)
    return move_choice
    # return movement_array.index(max(movement_array))


# initialize the game manager.
gm = GameManager(GAME_GRID_WIDTH, GAME_GRID_HEIGHT)

game_window = pg.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
pg.display.set_caption('ASSIGNMENT 2')
game_window.fill(BACKGROUND_COLOR)

font = pg.font.Font(os.path.join(ABS_PATH,"Retron2000.ttf"), 30)
run_game_loop = True


frame_count = 0

clock = pg.time.Clock()

while (run_game_loop):

    # Check for key presses
    # CONTROLS:
    # p -> Pause/unpause
    # Right Arrow -> If paused, progress one tick
    # Left Arrow -> If paused, rewind one tick
    # Esc -> Exit game
    # 0 -> Toggle scent_stacking (Not useful)
    for event in pg.event.get():
        if event.type == pg.KEYDOWN:
            if event.key == pg.K_ESCAPE:
                run_game_loop = False                    
            if event.key == pg.K_RIGHT:
                if gm.paused:
                    gm.logicTick()
                    gm.draw(game_window)
            if event.key == pg.K_LEFT:
                if gm.paused:
                    gm.rewindGameState(1)
                    gm.draw(game_window)
            if event.key == pg.K_p:
                gm.paused = not gm.paused
                gm.draw(game_window)

            if event.key == pg.K_0:
                SCENT_STACKING = not SCENT_STACKING
                gm.game_grid.calcSmellMatrix()
        # Check to see if the user has requested that the game end.
        if event.type == pg.QUIT:
            run_game_loop = False

    if not gm.paused:
        gm.logicTick()

        if frame_count > SKIP_FRAMES:
            gm.draw(game_window)
            frame_count = 0
        delta_time = clock.tick(FRAMES_PER_SECOND)

        frame_count += 1
