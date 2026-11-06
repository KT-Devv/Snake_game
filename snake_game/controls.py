"""Turns raw pygame events (keyboard, gamepad, touch swipes) into abstract action names.

Actions: up down left right confirm back pause menu mute fullscreen vol_up vol_down
Mouse clicks are handled by the app directly because they carry a screen position.
"""

import pygame

KEY_ACTIONS = {
    pygame.K_UP: "up", pygame.K_w: "up",
    pygame.K_DOWN: "down", pygame.K_s: "down",
    pygame.K_LEFT: "left", pygame.K_a: "left",
    pygame.K_RIGHT: "right", pygame.K_d: "right",
    pygame.K_RETURN: "confirm", pygame.K_KP_ENTER: "confirm", pygame.K_SPACE: "confirm",
    pygame.K_ESCAPE: "back",
    pygame.K_p: "pause",
    pygame.K_q: "menu",
    pygame.K_m: "mute",
    pygame.K_F11: "fullscreen",
    pygame.K_MINUS: "vol_down", pygame.K_KP_MINUS: "vol_down",
    pygame.K_EQUALS: "vol_up", pygame.K_PLUS: "vol_up", pygame.K_KP_PLUS: "vol_up",
}

# SDL's standard layout: A=0 B=1 X=2 Y=3 LB=4 RB=5 Back=6 Start=7
BUTTON_ACTIONS = {0: "confirm", 1: "back", 6: "menu", 7: "pause"}

AXIS_DEADZONE = 0.6
SWIPE_DISTANCE = 0.035   # fraction of the screen a finger must travel to count as a swipe


class InputMapper:
    def __init__(self):
        self._axis_state = {0: 0, 1: 0}
        self._fingers = {}

    def process(self, event):
        t = event.type
        if t == pygame.KEYDOWN:
            action = KEY_ACTIONS.get(event.key)
            return [action] if action else []

        if t == pygame.JOYHATMOTION:
            x, y = event.value
            out = []
            if x:
                out.append("right" if x > 0 else "left")
            if y:
                out.append("up" if y > 0 else "down")
            return out

        if t == pygame.JOYAXISMOTION and event.axis in self._axis_state:
            state = 0
            if event.value > AXIS_DEADZONE:
                state = 1
            elif event.value < -AXIS_DEADZONE:
                state = -1
            previous, self._axis_state[event.axis] = self._axis_state[event.axis], state
            if state and state != previous:  # fire once per push, not once per frame
                if event.axis == 0:
                    return ["right" if state > 0 else "left"]
                return ["down" if state > 0 else "up"]
            return []

        if t == pygame.JOYBUTTONDOWN:
            action = BUTTON_ACTIONS.get(event.button)
            return [action] if action else []

        if t == pygame.FINGERDOWN:
            self._fingers[event.finger_id] = (event.x, event.y)
            return []

        if t == pygame.FINGERMOTION and event.finger_id in self._fingers:
            ox, oy = self._fingers[event.finger_id]
            dx, dy = event.x - ox, event.y - oy
            if max(abs(dx), abs(dy)) >= SWIPE_DISTANCE:
                self._fingers[event.finger_id] = (event.x, event.y)  # allows chained swipes
                if abs(dx) > abs(dy):
                    return ["right" if dx > 0 else "left"]
                return ["down" if dy > 0 else "up"]
            return []

        if t == pygame.FINGERUP:
            self._fingers.pop(event.finger_id, None)
        return []
