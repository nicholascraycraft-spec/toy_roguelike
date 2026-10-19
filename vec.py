from dataclasses import dataclass
@dataclass(frozen=True, slots=True)
class Vec:
    x: int
    y: int
    def __add__(self, o): return Vec(self.x + o.x, self.y + o.y)
    def __sub__(self, o): return Vec(self.x - o.x, self.y - o.y)
    def __getitem__(self, key):
        return (self.x, self.y)[key]
    def neighbors(self):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx or dy:
                    yield Vec(self.x + dx, self.y + dy)


@dataclass(frozen=True, slots=True)
class Rect:
    x: int
    y: int
    w: int
    h: int
    def intersects(self, o):
        return (self.x < o.x + o.w and o.x < self.x + self.w
                and self.y < o.y + o.h and o.y < self.y + self.h)
    def inflate(self, n):
        return Rect(self.x - n, self.y - n, self.w + 2*n, self.h + 2*n)
    def cells(self):
        for y in range(self.y, self.y + self.h):
            for x in range(self.x, self.x + self.w):
                yield Vec(x, y)
    def center(self):
        return Vec(self.x + self.w // 2, self.y + self.h // 2)

def chebyshev(a, b):
    return max(abs(a.x - b.x), abs(a.y - b.y))