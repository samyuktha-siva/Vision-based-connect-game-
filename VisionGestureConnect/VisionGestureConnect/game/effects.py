"""Gentle visual effects: butterflies, smiley faces, sparkles and soft rings.

Everything moves slowly and fades smoothly (no flashing). When animations are
switched off, nothing here moves: the win screen shows a still picture instead.
"""

import math
import random

import pygame

from game.settings import COLOR_NAMES, COLOR_RGB


def draw_butterfly(surface, pos, size, color, flap=1.0):
    """A simple butterfly. `flap` between 0.4 and 1.0 changes the wing width."""
    x, y = pos
    w = max(2, int(size * 0.55 * flap))
    h = int(size * 0.7)
    dark = (30, 34, 56)
    for side in (-1, 1):
        upper = pygame.Rect(0, 0, w, h)
        upper.center = (x + side * w // 2, y - h // 4)
        lower = pygame.Rect(0, 0, int(w * 0.75), int(h * 0.7))
        lower.center = (x + side * int(w * 0.4), y + h // 3)
        pygame.draw.ellipse(surface, color, upper)
        pygame.draw.ellipse(surface, color, lower)
        pygame.draw.ellipse(surface, dark, upper, 2)
    pygame.draw.line(surface, dark, (x, y - h // 2), (x, y + h // 2), 3)


def draw_smiley(surface, pos, radius, color=(255, 214, 90)):
    x, y = int(pos[0]), int(pos[1])
    dark = (60, 45, 30)
    pygame.draw.circle(surface, color, (x, y), radius)
    pygame.draw.circle(surface, dark, (x, y), radius, 2)
    eye = max(2, radius // 6)
    pygame.draw.circle(surface, dark, (x - radius // 3, y - radius // 5), eye)
    pygame.draw.circle(surface, dark, (x + radius // 3, y - radius // 5), eye)
    smile = pygame.Rect(0, 0, int(radius * 1.2), int(radius * 1.0))
    smile.center = (x, y + radius // 6)
    pygame.draw.arc(surface, dark, smile, math.radians(200), math.radians(340), 3)


class _Particle:
    def __init__(self, kind, x, y, vx, vy, color, size, life):
        self.kind, self.x, self.y = kind, x, y
        self.vx, self.vy = vx, vy
        self.color, self.size = color, size
        self.life = self.max_life = life
        self.phase = random.random() * 6.28

    def update(self, dt):
        self.life -= dt
        self.phase += dt * 3.0                    # slow, gentle flapping
        self.x += (self.vx + math.sin(self.phase) * 12) * dt
        self.y += self.vy * dt

    @property
    def alpha(self):
        """Fade in and out smoothly."""
        age = self.max_life - self.life
        return max(0.0, min(1.0, age / 0.6, self.life / 0.8))


class Effects:
    def __init__(self):
        self.enabled = True
        self.particles = []
        self.rings = []          # [x, y, color, age]

    def clear(self):
        self.particles.clear()
        self.rings.clear()

    # -------------------------------------------------------------- spawn
    def celebrate(self, area):
        """Butterflies and smileys drifting up across `area` (a pygame.Rect)."""
        if not self.enabled:
            return
        rng = random.Random()
        for i in range(14):
            color = COLOR_RGB[COLOR_NAMES[i % len(COLOR_NAMES)]]
            kind = "smiley" if i % 4 == 3 else "butterfly"
            self.particles.append(_Particle(
                kind, rng.randint(area.left, area.right), area.bottom + rng.randint(0, 120),
                rng.uniform(-15, 15), rng.uniform(-70, -35), color,
                rng.randint(26, 40), rng.uniform(5.0, 8.0)))

    def sparkle(self, pos, color):
        if not self.enabled:
            return
        for i in range(8):
            ang = i * math.pi / 4
            self.particles.append(_Particle(
                "sparkle", pos[0], pos[1], math.cos(ang) * 40, math.sin(ang) * 40,
                color, 6, 1.2))

    def ring(self, pos, color):
        """A soft ring that fades out where an attempt was not allowed."""
        if self.enabled:
            self.rings.append([pos[0], pos[1], color, 0.0])

    # ------------------------------------------------------ update / draw
    def update(self, dt):
        for p in self.particles:
            p.update(dt)
        self.particles = [p for p in self.particles if p.life > 0]
        for r in self.rings:
            r[3] += dt
        self.rings = [r for r in self.rings if r[3] < 0.9]

    def draw(self, surface):
        for r in self.rings:
            fade = 1.0 - r[3] / 0.9
            color = tuple(int(c * fade + 40 * (1 - fade)) for c in r[2])
            pygame.draw.circle(surface, color, (int(r[0]), int(r[1])), int(18 + r[3] * 14), 3)
        for p in self.particles:
            a = p.alpha
            if p.kind == "butterfly":
                flap = 0.7 + 0.3 * math.sin(p.phase * 2)
                color = tuple(int(c * a + 30 * (1 - a)) for c in p.color)
                draw_butterfly(surface, (p.x, p.y), p.size, color, flap)
            elif p.kind == "smiley":
                color = tuple(int(c * a + 30 * (1 - a)) for c in (255, 214, 90))
                draw_smiley(surface, (p.x, p.y), p.size // 2, color)
            else:
                color = tuple(int(c * a + 30 * (1 - a)) for c in p.color)
                pygame.draw.circle(surface, color, (int(p.x), int(p.y)), p.size)

    def draw_still_celebration(self, surface, area):
        """Used instead of moving effects when animations are off."""
        for i in range(5):
            x = area.left + area.width * (i + 1) // 6
            y = area.top + 40 + (i % 2) * 25
            if i % 2 == 0:
                draw_butterfly(surface, (x, y), 34, COLOR_RGB[COLOR_NAMES[i]])
            else:
                draw_smiley(surface, (x, y), 18)
