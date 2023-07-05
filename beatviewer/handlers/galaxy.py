import math
import random

import pygame

from .pygame_handler import PygameHandler


class Dot:

    SPRITE_SIZE = 64

    def __init__(self, vmax, z0, base_color, base_radius, dz, blur=10):
        self.vmax = vmax
        self.z0 = z0
        self.base_color = base_color
        self.base_radius = base_radius
        self.x = 0
        self.y = 0
        self.z = 0
        self.px = 0
        self.py = 0
        self.vx = 0
        self.vy = 0
        self.ax = 0
        self.ay = 0
        self.dz = dz
        self.blur = blur
        self.reset(randomz=True)
        self.sprite = pygame.Surface((self.SPRITE_SIZE, self.SPRITE_SIZE), pygame.SRCALPHA)
        self.generate_sprite()

    def generate_sprite(self):
        center = self.SPRITE_SIZE // 2
        for i in range(self.SPRITE_SIZE):
            for j in range(self.SPRITE_SIZE):
                t = math.sqrt(math.pow(center - i, 2) + math.pow(center - j, 2)) / center
                alpha = 1 - math.pow(t, self.blur)
                alpha = 255 * max(0, min(1, alpha))
                self.sprite.set_at((i, j), (*self.base_color, alpha))

    def reset(self, randomz=False):
        if randomz:
            self.z = random.random()
        else:
            self.z = 1
        self.x = random.gauss(mu=0, sigma=0.2) / self.z0 * self.z
        self.y = random.gauss(mu=0, sigma=0.2) / self.z0 * self.z
        self._update_px_py()

    @property
    def radius(self):
        return self.base_radius / self.z
    
    @property
    def color(self):
        if self.z < .9:
            return self.base_color[:]
        g = (1 - self.z) / .1
        return [g * c for c in self.base_color]

    @property
    def out(self):
        return self.z <= 0 or self.px < 0 or self.px >= 1 or self.py < 0 or self.py >= 1

    def _update_px_py(self):
        self.px = self.x * self.z0 / self.z + .5
        self.py = self.y * self.z0 / self.z + .5

    @property
    def vnorm(self):
        return (self.vx ** 2 + self.vy ** 2) ** .5
    
    def push(self, direction, strength):
        self.ax = strength * direction[0]
        self.ay = strength * direction[1]
    
    def update(self, dz=0):
        if dz is None:
            dz = self.dz
        self.z += dz
        self.vx += self.ax
        self.vy += self.ay
        if self.vnorm > self.vmax:
            self.vx /= self.vnorm / self.vmax
            self.vy /= self.vnorm / self.vmax
        self.x += self.vx
        self.y += self.vy
        self._update_px_py()
        if self.out:
            self.reset()


def generate_random_direction(previous_direction=None):
    if previous_direction is None:
        previous_direction = [1, 0]
    x, y = previous_direction
    if x == 0:
        if y > 0:
            theta = math.pi / 2
        else:
            theta = - math.pi / 2
    else:
        theta = math.atan2(y, x)
    theta_mod = random.random() * math.pi - .5 * math.pi
    new_theta = theta + math.pi + theta_mod
    return [math.cos(new_theta), math.sin(new_theta)]


def generate_random_color():
    """
    https://clarkvision.com/articles/color-of-stars/
    """
    return random.choice([
        (103, 139, 201),
        (118, 140, 200),
        (121, 146, 200),
        (111, 143, 200),
        (116, 149, 200),
        (120, 150, 200),
        (130, 166, 200),
        (138, 174, 200),
        (132, 166, 201),
        (148, 176, 200),
        (152, 176, 200),
        (161, 184, 200),
        (164, 191, 200),
        (184, 200, 200),
        (193, 200, 193),
        (199, 200, 195),
        (193, 200, 192),
        (200, 200, 200),
        (191, 200, 173),
        (200, 181, 164),
        (201, 201, 165),
        (200, 195, 189),
        (200, 185, 162),
        (200, 179, 134),
        (201, 154, 112),
        (200, 162, 99),
        (200, 133, 65),
        (200, 141, 73),
        (200, 137, 84),
        (200, 119, 54),
        (200, 53, 46),
    ])


def blurred_circle(surface, dot, center):
    dest_size = int(dot.radius * 5)
    sprite = pygame.Surface((dest_size, dest_size), pygame.SRCALPHA)
    pygame.transform.scale(dot.sprite, (dest_size, dest_size), sprite)
    if dot.z >= .9:
        sprite.set_alpha(255 * (1 - dot.z) / .1)
    surface.blit(
        sprite,
        (center[0] - Dot.SPRITE_SIZE // 2, center[1] - Dot.SPRITE_SIZE // 2))


class Galaxy(PygameHandler):

    NAME = "galaxy"

    def __init__(
            self,
            pipe,
            width=1280,
            height=720,
            fullscreen=False,
            fps=60,
            n=200,
            dz=0.005,
            dxy=3,
            z0=0.1,
            vmax=0.1,
            bw=False,
            blur=10,
            random_dz=0,
            base_radius=1,
        ):
        PygameHandler.__init__(self, pipe, width, height, fullscreen, fps)
        self.n = n
        self.z0 = z0
        self.dz = dz
        self.dxz = dxy
        self.vmax = vmax
        self.bw = bw
        self.blur = blur
        self.random_dz = random_dz
        self.base_radius = base_radius
        self.previous_direction = None
        self.dots = []

    @staticmethod
    def add_arguments(parser):
        PygameHandler.add_arguments(parser)
        parser.add_argument("--n", type=int, default=200, help="Number of moving dots")
        parser.add_argument("--z0", type=float, default=0.1, help="Z-index (between 0 and 1) of the camera plane; lower values increase the FOV")
        parser.add_argument("--dz", type=float, default=0.015, help="Dot speed along the Z axis")
        parser.add_argument("--dxy", type=float, default=0.02, help="Acceleration amplitude for the XY axes; greater values will make beat impacts stronger")
        parser.add_argument("--vmax", type=float, default=0.05, help="Dot speed limit on the XY axes; both range from 0 to 1")
        parser.add_argument("--bw", action="store_true", help="Disable colors")
        parser.add_argument("--blur", type=int, default=2, help="Dot blurring factor; dots get sharper as the value increases")
        parser.add_argument("--random-dz", type=float, default=0, help="Z-axis speed deviation probability")
        parser.add_argument("--base-radius", type=float, default=1, help="Dot radius")

    @classmethod
    def from_args(cls, pipe, args):
        return cls.from_keys(
            pipe,
            args,
            [], 
            PygameHandler.BASE_KWARG_KEYS + ["n", "z0", "dz", "dxy", "vmax", "bw", "blur", "random_dz", "base_radius"])

    def setup(self):
        PygameHandler.setup(self, "BeatViewer: Galaxy")
        self.dots = []
        for _ in range(self.n):
            if self.bw:
                color = [255, 255, 255]
            else:
                color = generate_random_color()
            dzrange = self.random_dz * self.dz
            dz = self.dz + random.random() * 2 * dzrange - dzrange
            dot = Dot(self.vmax, self.z0, color, self.base_radius, -dz, self.blur)
            self.dots.append(dot)
    
    def push_dots(self):
        self.previous_direction = generate_random_direction(self.previous_direction)
        for dot in self.dots:
            dot.push(self.previous_direction[:], self.dxz)

    def handle_beat(self):
        self.push_dots()

    def update(self):
        self.window.fill((0, 0, 0))
        for dot in self.dots:
            dot.update(dz=None)
        self.dots.sort(key=lambda d: -d.z)
        for dot in self.dots:
            blurred_circle(self.window, dot, (dot.px * self.width, dot.py * self.height))
