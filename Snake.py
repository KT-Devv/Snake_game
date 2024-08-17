import pygame
import time
import random
import os

# Initialize the game
pygame.init()
pygame.mixer.init()

# Define colors
white = (255, 255, 255)
yellow = (255, 255, 102)
black = (0, 0, 0)
red = (213, 50, 80)
green = (0, 255, 0)
blue = (50, 153, 213)
purple = (128, 0, 128)
gray = (100, 100, 100)

# Set display dimensions
width = 600
height = 400

# Set snake block size
block_size = 20
special_food_size = 30

# Set display
dis = pygame.display.set_mode((width, height))
pygame.display.set_caption('Snake Game')

# Load background image
bg_image = pygame.image.load("background.jpg")  # Replace with your background image path
bg_image = pygame.transform.scale(bg_image, (width, height))

# Define fonts
font_style = pygame.font.Font("arialmt.ttf", 10)  # Smaller font for status bar text
score_font = pygame.font.Font("PressStart2P-Regular.ttf", 10)  # Adjust as needed

# Load sound effects
eat_sound = pygame.mixer.Sound("eat_sound.mp3")  # Replace with your sound file
game_over_sound = pygame.mixer.Sound("game-over.mp3")  # Replace with your sound file
pygame.mixer.music.load("bg.mp3")  # Replace with your music file
pygame.mixer.music.play(-1)  # Loop the music

# High score file
high_score_file = "high_score.txt"

# Load snake image
snake_image = pygame.image.load("snake.jpg")  # Replace with your snake image path
snake_image = pygame.transform.scale(snake_image, (block_size, block_size))

# Initialize clock
clock = pygame.time.Clock()

def load_high_score():
    if os.path.exists(high_score_file):
        with open(high_score_file, "r") as f:
            return int(f.read().strip())
    return 0

def save_high_score(score):
    with open(high_score_file, "w") as f:
        f.write(str(score))

def draw_snake(snake_list):
    for i, x in enumerate(snake_list):
        pygame.draw.ellipse(dis, green, [x[0], x[1], block_size, block_size])

def draw_food(foodx, foody):
    pygame.draw.rect(dis, red, [foodx, foody, block_size, block_size])


def draw_special_food(foodx, foody):
    pygame.draw.rect(dis, purple, [foodx, foody, special_food_size, special_food_size])

def draw_score(score, high_score, elapsed_time):
    value = score_font.render(f"Score: {score}", True, black)
    dis.blit(value, [20, 10])
    high_value = score_font.render(f"High Score: {high_score}", True, black)
    dis.blit(high_value, [width - 150, 10])
    time_value = score_font.render(f"Time: {elapsed_time}s", True, black)
    dis.blit(time_value, [width // 2 - time_value.get_width() // 2, 10])

def message(msg, color):
    mesg = font_style.render(msg, True, color)
    dis.blit(mesg, [width // 2 - mesg.get_width() // 2, height // 2 - mesg.get_height() // 2])

def game_intro():
    dis.blit(bg_image, (0, 0))  # Draw the background image
    message("Press 1 for Easy, 2 for Medium, 3 for Hard", white)
    pygame.display.update()
    
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                quit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    return 10, green  # Easy speed
                if event.key == pygame.K_2:
                    return 15, yellow  # Medium speed
                if event.key == pygame.K_3:
                    return 20, red  # Hard speed

def gameLoop():
    high_score = load_high_score()
    snake_speed, snake_color = game_intro()

    game_over = False
    game_close = False

    x1 = width / 2
    y1 = height / 2

    x1_change = 0
    y1_change = 0

    snake_List = []
    Length_of_snake = 1

    foodx = round(random.randrange(0, width - block_size) / block_size) * block_size
    foody = round(random.randrange(0, height - block_size) / block_size) * block_size

    special_foodx = None
    special_foody = None
    special_food_time = 0
    special_food_duration = 5000  # Special food lasts for 5 seconds
    special_food_delay = 10000  # Delay before special food can reappear
    last_special_food_eaten = 0

    start_time = pygame.time.get_ticks()  # Start the timer

    # Initialize direction
    direction = 'right'

    while not game_over:
        while game_close:
            dis.blit(bg_image, (0, 0))  # Draw the background image
            message("You Lost! Press C to Play Again or Q to Quit, or ESC to Exit", red)
            elapsed_time = (pygame.time.get_ticks() - start_time) // 1000  # Update elapsed time
            draw_score(Length_of_snake - 1, high_score, elapsed_time)
            pygame.display.update()
            game_over_sound.play()
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_q:
                        game_over = True
                        game_close = False
                    elif event.key == pygame.K_c:
                        gameLoop()
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        quit

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                game_over = True
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    quit()
                if event.key == pygame.K_LEFT and x1_change == 0:
                    x1_change = -block_size
                    y1_change = 0
                    direction = 'left'
                elif event.key == pygame.K_RIGHT and x1_change == 0:
                    x1_change = block_size
                    y1_change = 0
                    direction = 'right'
                elif event.key == pygame.K_UP and y1_change == 0:
                    y1_change = -block_size
                    x1_change = 0
                    direction = 'up'
                elif event.key == pygame.K_DOWN and y1_change == 0:
                    y1_change = block_size
                    x1_change = 0
                    direction = 'down'

        if x1 >= width or x1 < 0 or y1 >= height or y1 < 0:
            game_close = True

        # Update the snake position
        x1 += x1_change
        y1 += y1_change

        # Check collision with itself
        snake_Head = [x1, y1]
        snake_List.append(snake_Head)
        if len(snake_List) > Length_of_snake:
            del snake_List[0]

        for x in snake_List[:-1]:
            if x == snake_Head:
                game_close = True

        dis.blit(bg_image, (0, 0))  # Draw the background image

        # Draw the food
        draw_food(foodx, foody)

        # Special food appearance logic
        current_time = pygame.time.get_ticks()
        if (special_foodx is None and
            current_time - last_special_food_eaten > special_food_delay and
            random.randint(1, 100) <= 5):
            special_foodx = round(random.randrange(0, width - special_food_size) / block_size) * block_size
            special_foody = round(random.randrange(0, height - special_food_size) / block_size) * block_size
            special_food_time = current_time

        if special_foodx is not None:
            if current_time - special_food_time < special_food_duration:
                draw_special_food(special_foodx, special_foody)
            else:
                special_foodx = None
                special_foody = None

        draw_snake(snake_List)  # Draw the snake

        elapsed_time = (pygame.time.get_ticks() - start_time) // 1000  # Update elapsed time
        draw_score(Length_of_snake - 1, high_score, elapsed_time)  # Update the score and timer display

        pygame.display.update()

        # Check if the snake has eaten the food
        if x1 == foodx and y1 == foody:
            foodx = round(random.randrange(0, width - block_size) / block_size) * block_size
            foody = round(random.randrange(0, height - block_size) / block_size) * block_size
            Length_of_snake += 1
            eat_sound.play()
            if Length_of_snake - 1 > high_score:
                high_score = Length_of_snake - 1

        # Check if the snake has eaten the special food
        if special_foodx is not None and x1 < special_foodx + special_food_size and x1 + block_size > special_foodx and y1 < special_foody + special_food_size and y1 + block_size > special_foody:
            special_foodx = None
            special_foody = None
            Length_of_snake += 3
            eat_sound.play()

        # Check for illegal moves (opposite direction)
        if direction == 'left' and x1_change == block_size:
            game_close = True
        elif direction == 'right' and x1_change == -block_size:
            game_close = True
        elif direction == 'up' and y1_change == block_size:
            game_close = True
        elif direction == 'down' and y1_change == -block_size:
            game_close = True

        clock.tick(snake_speed)  # Keep a constant speed

    save_high_score(high_score)
    pygame.quit()
    quit()

gameLoop()
