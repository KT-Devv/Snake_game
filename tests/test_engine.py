import pygame

pygame.init()
pygame.mixer.init()

try:
    game_over_sound = pygame.mixer.Sound("game-over.mp3") 
    print("Sound loaded successfully!")
except Exception as e:
    print("Error loading sound:", e)