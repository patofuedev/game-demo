"""Space Invaders estilo arcade, hecho con pygame.

Controles:
    ← / → o A / D   mover
    ESPACIO         disparar
    P               pausa
    ESC             salir
"""
import json
import random
import sys
from pathlib import Path

import pygame

WIDTH, HEIGHT = 800, 700
FPS = 60
HISCORE_FILE = Path(__file__).with_name("hiscore.json")

BLACK = (0, 0, 0)
WHITE = (240, 240, 240)
GREEN = (60, 255, 90)
RED = (255, 60, 60)
YELLOW = (255, 220, 60)
CYAN = (60, 220, 255)
MAGENTA = (255, 90, 220)

# Sprites en pixel-art: cada '#' es un píxel.
INVADER_SPRITES = {
    0: [  # calamar
        [
            "...##...",
            "..####..",
            ".######.",
            "##.##.##",
            "########",
            "..#..#..",
            ".#.##.#.",
            "#.#..#.#",
        ],
        [
            "...##...",
            "..####..",
            ".######.",
            "##.##.##",
            "########",
            ".#.##.#.",
            "#......#",
            ".#....#.",
        ],
    ],
    1: [  # cangrejo
        [
            "..#...#..",
            "...#.#...",
            "..#####..",
            ".##.#.##.",
            "#########",
            "#.#####.#",
            "#.#...#.#",
            "...##.##.",
        ],
        [
            "..#...#..",
            "#..#.#..#",
            "#.#####.#",
            "###.#.###",
            "#########",
            ".#######.",
            "..#...#..",
            ".#.....#.",
        ],
    ],
    2: [  # pulpo
        [
            "....####....",
            ".##########.",
            "############",
            "###..##..###",
            "############",
            "...##..##...",
            "..##.##.##..",
            "##........##",
        ],
        [
            "....####....",
            ".##########.",
            "############",
            "###..##..###",
            "############",
            "..###..###..",
            ".##..##..##.",
            "..##....##..",
        ],
    ],
}
INVADER_COLORS = {0: MAGENTA, 1: CYAN, 2: GREEN}
INVADER_POINTS = {0: 30, 1: 20, 2: 10}

PLAYER_SPRITE = [
    ".......#.......",
    "......###......",
    "......###......",
    ".#############.",
    "###############",
    "###############",
    "###############",
]
UFO_SPRITE = [
    ".....######.....",
    "...##########...",
    "..############..",
    ".##.##.##.##.##.",
    "################",
    "..###..##..###..",
    "...#........#...",
]


def make_sprite(rows, color, px):
    surf = pygame.Surface((len(rows[0]) * px, len(rows) * px), pygame.SRCALPHA)
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            if ch == "#":
                pygame.draw.rect(surf, color, (x * px, y * px, px, px))
    return surf


class Bullet:
    def __init__(self, x, y, vy, color):
        self.rect = pygame.Rect(0, 0, 4, 14)
        self.rect.midbottom = (x, y)
        self.vy = vy
        self.color = color

    def update(self):
        self.rect.y += self.vy

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)


class Player:
    SPEED = 6
    COOLDOWN = 350  # ms

    def __init__(self):
        self.image = make_sprite(PLAYER_SPRITE, GREEN, 3)
        self.rect = self.image.get_rect(midbottom=(WIDTH // 2, HEIGHT - 30))
        self.last_shot = 0

    def update(self, keys):
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        self.rect.x += dx * self.SPEED
        self.rect.clamp_ip(pygame.Rect(10, 0, WIDTH - 20, HEIGHT))

    def try_shoot(self, now):
        if now - self.last_shot >= self.COOLDOWN:
            self.last_shot = now
            return Bullet(self.rect.centerx, self.rect.top, -10, WHITE)
        return None


class Invader:
    def __init__(self, kind, x, y):
        self.kind = kind
        self.frames = [make_sprite(f, INVADER_COLORS[kind], 3) for f in INVADER_SPRITES[kind]]
        self.rect = self.frames[0].get_rect(center=(x, y))


class Fleet:
    COLS, ROWS = 11, 5
    GAP_X, GAP_Y = 52, 46

    def __init__(self, level):
        self.invaders = []
        kinds = [0, 1, 1, 2, 2]
        top = 90 + min(level - 1, 5) * 12
        left = (WIDTH - (self.COLS - 1) * self.GAP_X) // 2
        for r in range(self.ROWS):
            for c in range(self.COLS):
                self.invaders.append(Invader(kinds[r], left + c * self.GAP_X, top + r * self.GAP_Y))
        self.total = len(self.invaders)
        self.dir = 1
        self.frame = 0
        self.step_timer = 0
        self.level = level

    def step_delay(self):
        # Menos invasores => más rápido (ms entre pasos).
        ratio = len(self.invaders) / self.total
        base = 700 - (self.level - 1) * 50
        return max(40, int(base * ratio))

    def update(self, dt):
        self.step_timer += dt
        if self.step_timer < self.step_delay():
            return
        self.step_timer = 0
        self.frame ^= 1
        left = min(i.rect.left for i in self.invaders)
        right = max(i.rect.right for i in self.invaders)
        if (self.dir > 0 and right + 14 >= WIDTH - 10) or (self.dir < 0 and left - 14 <= 10):
            self.dir *= -1
            for i in self.invaders:
                i.rect.y += 22
        else:
            for i in self.invaders:
                i.rect.x += 14 * self.dir

    def shooters(self):
        """Invasores más bajos de cada columna."""
        cols = {}
        for i in self.invaders:
            key = i.rect.centerx // 10
            if key not in cols or i.rect.y > cols[key].rect.y:
                cols[key] = i
        return list(cols.values())

    def lowest(self):
        return max(i.rect.bottom for i in self.invaders)

    def draw(self, screen):
        for i in self.invaders:
            screen.blit(i.frames[self.frame], i.rect)


class Bunker:
    """Búnker destructible: una rejilla de bloques que desaparecen al recibir impactos."""
    BLOCK = 6
    SHAPE = [
        "...##########...",
        "..############..",
        ".##############.",
        "################",
        "################",
        "################",
        "####........####",
        "###..........###",
    ]

    def __init__(self, x, y):
        self.blocks = []
        for r, row in enumerate(self.SHAPE):
            for c, ch in enumerate(row):
                if ch == "#":
                    self.blocks.append(pygame.Rect(x + c * self.BLOCK, y + r * self.BLOCK, self.BLOCK, self.BLOCK))

    def hit(self, bullet_rect):
        """Devuelve True si la bala impacta; destruye bloques cercanos."""
        hit = [b for b in self.blocks if b.colliderect(bullet_rect)]
        if not hit:
            return False
        center = hit[0].center
        for b in list(self.blocks):
            if abs(b.centerx - center[0]) <= self.BLOCK and abs(b.centery - center[1]) <= self.BLOCK * 1.5:
                if random.random() < 0.8:
                    self.blocks.remove(b)
        if hit[0] in self.blocks:
            self.blocks.remove(hit[0])
        return True

    def erode(self, rect):
        for b in [b for b in self.blocks if b.colliderect(rect)]:
            self.blocks.remove(b)

    def draw(self, screen):
        for b in self.blocks:
            pygame.draw.rect(screen, GREEN, b)


class Ufo:
    def __init__(self):
        self.image = make_sprite(UFO_SPRITE, RED, 3)
        self.dir = random.choice((-1, 1))
        x = -50 if self.dir > 0 else WIDTH + 50
        self.rect = self.image.get_rect(center=(x, 60))
        self.points = random.choice((50, 100, 150, 300))

    def update(self):
        self.rect.x += 3 * self.dir

    def offscreen(self):
        return self.rect.right < -60 or self.rect.left > WIDTH + 60


class Particle:
    def __init__(self, pos, color):
        self.x, self.y = pos
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-3, 3)
        self.life = random.randint(15, 30)
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.life -= 1

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, (self.x, self.y, 3, 3))


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("SPACE INVADERS")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 22, bold=True)
        self.big = pygame.font.SysFont("monospace", 56, bold=True)
        self.stars = [(random.randrange(WIDTH), random.randrange(HEIGHT), random.choice((1, 2))) for _ in range(80)]
        self.hiscore = self.load_hiscore()
        self.state = "menu"
        self.paused = False

    # --- persistencia ---
    def load_hiscore(self):
        try:
            return int(json.loads(HISCORE_FILE.read_text())["hiscore"])
        except (OSError, ValueError, KeyError):
            return 0

    def save_hiscore(self):
        try:
            HISCORE_FILE.write_text(json.dumps({"hiscore": self.hiscore}))
        except OSError:
            pass

    # --- estado de partida ---
    def new_game(self):
        self.score = 0
        self.lives = 3
        self.level = 1
        self.player = Player()
        self.start_level()
        self.state = "playing"

    def start_level(self):
        self.fleet = Fleet(self.level)
        self.bunkers = [Bunker(x - 48, HEIGHT - 150) for x in (130, 330, 530, 730)]
        self.player_bullet = None
        self.enemy_bullets = []
        self.ufo = None
        self.ufo_timer = random.randint(8000, 15000)
        self.particles = []
        self.respawn_timer = 0

    def explode(self, pos, color, n=14):
        self.particles += [Particle(pos, color) for _ in range(n)]

    def add_score(self, pts):
        self.score += pts
        if self.score > self.hiscore:
            self.hiscore = self.score

    def lose_life(self):
        self.explode(self.player.rect.center, GREEN, 30)
        self.lives -= 1
        self.enemy_bullets.clear()
        self.player_bullet = None
        if self.lives <= 0:
            self.save_hiscore()
            self.state = "gameover"
        else:
            self.respawn_timer = 90  # frames de invulnerabilidad/pausa

    # --- lógica ---
    def update(self, dt):
        keys = pygame.key.get_pressed()
        now = pygame.time.get_ticks()

        if self.respawn_timer > 0:
            self.respawn_timer -= 1
        else:
            self.player.update(keys)
            if keys[pygame.K_SPACE] and self.player_bullet is None:
                self.player_bullet = self.player.try_shoot(now)

        self.fleet.update(dt)

        # Disparos enemigos
        max_bullets = 2 + self.level
        if len(self.enemy_bullets) < max_bullets and random.random() < 0.02 + 0.004 * self.level:
            s = random.choice(self.fleet.shooters())
            self.enemy_bullets.append(Bullet(s.rect.centerx, s.rect.bottom + 12, 5 + self.level // 2, YELLOW))

        # OVNI
        self.ufo_timer -= dt
        if self.ufo is None and self.ufo_timer <= 0:
            self.ufo = Ufo()
        if self.ufo:
            self.ufo.update()
            if self.ufo.offscreen():
                self.ufo = None
                self.ufo_timer = random.randint(10000, 20000)

        # Bala del jugador
        b = self.player_bullet
        if b:
            b.update()
            if b.rect.bottom < 0:
                self.player_bullet = None
            else:
                self.resolve_player_bullet(b)

        # Balas enemigas
        for eb in self.enemy_bullets[:]:
            eb.update()
            if eb.rect.top > HEIGHT:
                self.enemy_bullets.remove(eb)
                continue
            if any(bk.hit(eb.rect) for bk in self.bunkers):
                self.enemy_bullets.remove(eb)
                continue
            if self.respawn_timer == 0 and eb.rect.colliderect(self.player.rect):
                self.enemy_bullets.remove(eb)
                self.lose_life()
                break

        # Invasores contra búnkers / suelo
        for inv in self.fleet.invaders:
            for bk in self.bunkers:
                bk.erode(inv.rect)
        if self.fleet.invaders and self.fleet.lowest() >= self.player.rect.top:
            self.lives = 1
            self.lose_life()

        for p in self.particles[:]:
            p.update()
            if p.life <= 0:
                self.particles.remove(p)

        if not self.fleet.invaders and self.state == "playing":
            self.level += 1
            self.start_level()

    def resolve_player_bullet(self, b):
        for bk in self.bunkers:
            if bk.hit(b.rect):
                self.player_bullet = None
                return
        for inv in self.fleet.invaders:
            if b.rect.colliderect(inv.rect):
                self.fleet.invaders.remove(inv)
                self.add_score(INVADER_POINTS[inv.kind])
                self.explode(inv.rect.center, INVADER_COLORS[inv.kind])
                self.player_bullet = None
                return
        if self.ufo and b.rect.colliderect(self.ufo.rect):
            self.add_score(self.ufo.points)
            self.explode(self.ufo.rect.center, RED, 25)
            self.ufo = None
            self.ufo_timer = random.randint(10000, 20000)
            self.player_bullet = None
            return
        for eb in self.enemy_bullets:
            if b.rect.colliderect(eb.rect):
                self.enemy_bullets.remove(eb)
                self.player_bullet = None
                return

    # --- dibujo ---
    def text(self, msg, font, color, center=None, topleft=None, topright=None):
        surf = font.render(msg, True, color)
        rect = surf.get_rect()
        if center:
            rect.center = center
        elif topleft:
            rect.topleft = topleft
        elif topright:
            rect.topright = topright
        self.screen.blit(surf, rect)

    def draw_background(self):
        self.screen.fill(BLACK)
        for x, y, s in self.stars:
            pygame.draw.rect(self.screen, (90, 90, 120), (x, y, s, s))

    def draw_hud(self):
        self.text(f"SCORE {self.score:05d}", self.font, WHITE, topleft=(15, 10))
        self.text(f"HI {self.hiscore:05d}", self.font, YELLOW, center=(WIDTH // 2, 22))
        self.text(f"NIVEL {self.level}", self.font, CYAN, topright=(WIDTH - 15, 10))
        pygame.draw.line(self.screen, GREEN, (0, HEIGHT - 12), (WIDTH, HEIGHT - 12), 2)
        icon = make_sprite(PLAYER_SPRITE, GREEN, 2)
        for i in range(self.lives):
            self.screen.blit(icon, (15 + i * 40, 42))

    def draw_game(self):
        self.draw_background()
        self.draw_hud()
        for bk in self.bunkers:
            bk.draw(self.screen)
        self.fleet.draw(self.screen)
        if self.ufo:
            self.screen.blit(self.ufo.image, self.ufo.rect)
        if self.respawn_timer == 0 or (self.respawn_timer // 6) % 2 == 0:
            if self.state == "playing":
                self.screen.blit(self.player.image, self.player.rect)
        if self.player_bullet:
            self.player_bullet.draw(self.screen)
        for eb in self.enemy_bullets:
            eb.draw(self.screen)
        for p in self.particles:
            p.draw(self.screen)

    def draw_menu(self):
        self.draw_background()
        self.text("SPACE", self.big, GREEN, center=(WIDTH // 2, 190))
        self.text("INVADERS", self.big, GREEN, center=(WIDTH // 2, 260))
        y = 360
        for kind, label in ((0, "= 30 PTS"), (1, "= 20 PTS"), (2, "= 10 PTS")):
            img = make_sprite(INVADER_SPRITES[kind][0], INVADER_COLORS[kind], 3)
            self.screen.blit(img, img.get_rect(center=(WIDTH // 2 - 70, y)))
            self.text(label, self.font, WHITE, topleft=(WIDTH // 2 - 20, y - 12))
            y += 40
        ufo = make_sprite(UFO_SPRITE, RED, 2)
        self.screen.blit(ufo, ufo.get_rect(center=(WIDTH // 2 - 70, y)))
        self.text("= ???", self.font, WHITE, topleft=(WIDTH // 2 - 20, y - 12))
        if (pygame.time.get_ticks() // 500) % 2 == 0:
            self.text("PULSA ENTER PARA JUGAR", self.font, YELLOW, center=(WIDTH // 2, 580))
        self.text("← → mover   ESPACIO disparar   P pausa", self.font, (140, 140, 140), center=(WIDTH // 2, 630))
        self.text(f"RECORD {self.hiscore:05d}", self.font, CYAN, center=(WIDTH // 2, 670))

    def draw_overlay(self, title, subtitle):
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 150))
        self.screen.blit(shade, (0, 0))
        self.text(title, self.big, RED if title == "GAME OVER" else YELLOW, center=(WIDTH // 2, HEIGHT // 2 - 30))
        self.text(subtitle, self.font, WHITE, center=(WIDTH // 2, HEIGHT // 2 + 40))

    # --- bucle principal ---
    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.quit()
                    elif self.state in ("menu", "gameover") and event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        self.new_game()
                    elif self.state == "playing" and event.key == pygame.K_p:
                        self.paused = not self.paused

            if self.state == "menu":
                self.draw_menu()
            else:
                if self.state == "playing" and not self.paused:
                    self.update(dt)
                self.draw_game()
                if self.paused:
                    self.draw_overlay("PAUSA", "Pulsa P para continuar")
                elif self.state == "gameover":
                    self.draw_overlay("GAME OVER", f"Puntos: {self.score}   ENTER para reintentar")
            pygame.display.flip()

    def quit(self):
        self.save_hiscore()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Game().run()
