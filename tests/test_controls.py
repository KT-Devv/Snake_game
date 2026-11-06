import unittest

import pygame

from snake_game.controls import InputMapper


def ev(type_, **kw):
    return pygame.event.Event(type_, **kw)


class ControlsTests(unittest.TestCase):
    def setUp(self):
        self.m = InputMapper()

    def test_keyboard(self):
        self.assertEqual(self.m.process(ev(pygame.KEYDOWN, key=pygame.K_LEFT)), ["left"])
        self.assertEqual(self.m.process(ev(pygame.KEYDOWN, key=pygame.K_w)), ["up"])
        self.assertEqual(self.m.process(ev(pygame.KEYDOWN, key=pygame.K_SPACE)), ["confirm"])
        self.assertEqual(self.m.process(ev(pygame.KEYDOWN, key=pygame.K_ESCAPE)), ["back"])
        self.assertEqual(self.m.process(ev(pygame.KEYDOWN, key=pygame.K_z)), [])

    def test_gamepad_hat(self):
        self.assertEqual(self.m.process(ev(pygame.JOYHATMOTION, value=(1, 0))), ["right"])
        self.assertEqual(self.m.process(ev(pygame.JOYHATMOTION, value=(0, 1))), ["up"])
        self.assertEqual(self.m.process(ev(pygame.JOYHATMOTION, value=(0, 0))), [])

    def test_gamepad_stick_fires_once_per_push(self):
        push = lambda v: self.m.process(ev(pygame.JOYAXISMOTION, axis=0, value=v))
        self.assertEqual(push(0.2), [])            # inside the deadzone
        self.assertEqual(push(0.9), ["right"])
        self.assertEqual(push(1.0), [])            # still held
        self.assertEqual(push(0.0), [])
        self.assertEqual(push(-0.9), ["left"])
        down = self.m.process(ev(pygame.JOYAXISMOTION, axis=1, value=0.9))
        self.assertEqual(down, ["down"])

    def test_gamepad_buttons(self):
        self.assertEqual(self.m.process(ev(pygame.JOYBUTTONDOWN, button=0)), ["confirm"])
        self.assertEqual(self.m.process(ev(pygame.JOYBUTTONDOWN, button=1)), ["back"])
        self.assertEqual(self.m.process(ev(pygame.JOYBUTTONDOWN, button=7)), ["pause"])
        self.assertEqual(self.m.process(ev(pygame.JOYBUTTONDOWN, button=9)), [])

    def test_touch_swipes(self):
        self.m.process(ev(pygame.FINGERDOWN, finger_id=1, x=0.5, y=0.5))
        self.assertEqual(self.m.process(ev(pygame.FINGERMOTION, finger_id=1, x=0.51, y=0.5)), [])  # jitter
        self.assertEqual(self.m.process(ev(pygame.FINGERMOTION, finger_id=1, x=0.60, y=0.5)), ["right"])
        # chained swipe without lifting the finger
        self.assertEqual(self.m.process(ev(pygame.FINGERMOTION, finger_id=1, x=0.60, y=0.70)), ["down"])
        self.m.process(ev(pygame.FINGERUP, finger_id=1, x=0.6, y=0.7))
        self.assertEqual(self.m.process(ev(pygame.FINGERMOTION, finger_id=1, x=0.1, y=0.1)), [])

    def test_swipe_up_and_left(self):
        self.m.process(ev(pygame.FINGERDOWN, finger_id=2, x=0.5, y=0.5))
        self.assertEqual(self.m.process(ev(pygame.FINGERMOTION, finger_id=2, x=0.5, y=0.4)), ["up"])
        self.assertEqual(self.m.process(ev(pygame.FINGERMOTION, finger_id=2, x=0.4, y=0.4)), ["left"])


if __name__ == "__main__":
    unittest.main()
