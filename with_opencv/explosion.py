#!/usr/bin/env python3
# -*- coding: UTF-8 -*-

## explosion.py


import os
import random
import operator
import threading
import numpy as np
import cv2
from time import time, sleep
print("Version OpenCV", cv2.__version__)

LARG = 1200
HAUT = 800


def get_black_image():
    return np.zeros((HAUT, LARG, 1), np.uint8)

# Permet de placer les lines de chaque thread
# LINES = { 1: DynamicExplosion() du thread 1,
#           2: DynamicExplosion() du thread 2}
LINES = {}


class HalfWave:
    '''Une demi onde: O A B C'''

    def __init__(self, O, start, gap, ampli, sens=0):
        '''O est l'origine = tuple x, y
        start = début de l'onde = OA
        gap = décalage du point C = AC
        ampli = amplitude de l'onde
        sens = vers le haut ou vers le bas
        draw = 1 pour réellement dessiner la courbe
        '''

        self.start = int(start)
        self.gap = int(gap)
        self.ampli = int(ampli)

        if sens not in [0, 1]:
            self.sens = 1
        else:
            self.sens = sens

        # Tous les points devront être corrigés de O(Ox, Oy)
        self.O = O

        self.set_ABC()

    def set_ABC(self):
        '''Les points sont comptés à partir de O'''

        self.A = (self.start, 0)

        if self.sens:
            self.B = (int(self.start + self.gap/2), - self.ampli)
        else:
            self.B = (int(self.start + self.gap/2), self.ampli)

        self.C = (self.start + self.gap, 0)

    def get_3_line(self):
        '''Droite de A à B et de B à C'''

        a = t_s(self.A, self.O)
        b = t_s(self.B, self.O)
        c = t_s(self.C, self.O)

        # Droite de A à B
        line1 = get_line(a, b)
        # Droite de B à C
        line2 = get_line(b, c)

        # La liste des points des 2 lignes
        line = line1 + line2

        return line

    def draw_half_wave(self, img):
        '''Droite de A à B et de B à C'''

        a = t_s(self.A, self.O)
        b = t_s(self.B, self.O)
        c = t_s(self.C, self.O)

        # Droite de A à B
        img= draw_line(img, a, b)
        # Droite de B à C
        img= draw_line(img, b, c)

        return img


class Wave(dict):
    '''Onde de n demi-sinusoïdal static
    self hérite de dict: attributs et méthodes
    n maxi 10
    Les points sont les sommets de chaque demi-sinusoïdale
    line = liste des points d'une demi-sinusoïdales
    lines = liste des tous les points de toutes les demi-sinusoïdales
    '''

    def __init__(self, n, O, start, gap, ampli):
        super().__init__()

        self.n = n
        self.O = O
        self.start = start
        self.gap = gap
        self.ampli = ampli

        # Les points sommets de toutes les demi-sinusoïdales
        wave_points = self.get_wave_points()

        for i in range(self.n):
            if i % 2 == 0:
                sens = 0
            else:
                sens = 1

            # O, start, gap, ampli, sens=0
            self[i] = HalfWave( self.O,
                                wave_points[i][0],
                                wave_points[i][1],
                                self.ampli*0.8**i,
                                sens )

    def get_wave_points(self):
        start = self.start
        gap = self.gap

        points = [(start, gap)]
        for i in range(self.n-1):
            toto = points[i][0] + points[i][1], gap*(1-0.1*(i+1))
            points.append(toto)

        return points

    def get_lines(self):
        '''Retourne l'image avec le dessin des points,
        et crée la liste des points de toutes les courbes.'''

        lines = []
        for i in range(self.n):
            line = self[i].get_3_line()
            lines = lines + line

        return lines

    def draw_waves(self, img):
        '''Retourne l'image avec le dessin des points,
        et crée la liste des points de toutes les courbes.'''

        for i in range(self.n):
            img = self[i].draw_half_wave(img)

        return img


class StaticExplosion:
    '''Chaque point de Wave devient un cercle de couleur de l'amplitude.'''

    def __init__(self, O, n, start, gap, ampli, pixel):
        '''points = liste de point (x, y).
        O centre
        n nombre de demi-sinusoïdales
        start point A = début par rapport à O
        gap ecart entre A et C
        ampli amplitude de la première demi-sinusoïdales
        pixel epaisseur des cercles
        '''

        self.O = O
        self.n = n
        self. start = start
        self.gap = gap
        self.ampli = ampli
        self.pixel = pixel
        self.get_lines()

    def get_lines(self):
        self.sinus = Wave(  self.n,
                            self.O,
                            self. start,
                            self.gap,
                            self.ampli)

        self.lines = self.sinus.get_lines()

    def draw_opencv_circle(self, img, C, color, radius):

        centre = C
        thickness = self.pixel

        lt = cv2.LINE_AA  # antialiased line

        img = cv2.circle(   img,
                            centre,
                            radius,
                            color,
                            thickness,
                            lineType = lt)
        return img

    def lines_to_circle(self, img):

        for point in self.lines:
            x = point[0]
            y = point[1]
            if self.ampli != 0:
                color = abs((y - self.O[1])/self.ampli) * 255
                color = int(min(color, 255))
            else:
                color = 0

            if x % self.pixel == 0:
                radius = int(x - self.O[0])
                img = self.draw_opencv_circle(img, self.O, color, radius)

        return img


class DynamicExplosion:
    '''Les cercles créés par StaticExplosion explosent !!'''

    def __init__(self, O, n, start, gap, ampli, pixel, slide, decrease):

        self.O = O
        self.n = n
        self.start = start
        self.gap = gap
        self.ampli = ampli
        self.pixel = pixel
        self.slide = slide
        self.t_zero = time()
        self.decrease = decrease

    def get_lines_at_t(self):

        delta_t = time() - self.t_zero

        C = self.O

        self.start += (self.slide/60)*delta_t
        self.gap = self.gap + (self.slide/60) * delta_t
        self.ampli = self.ampli - (self.decrease/30)*delta_t

        if self.ampli < 0:
            self.ampli = 0

        self.static_explosion = StaticExplosion(    C,
                                                    self.n,
                                                    self.start,
                                                    self.gap,
                                                    self.ampli,
                                                    self.pixel)

        return self.static_explosion.lines

    def explosion(self, img):

        lines = self.get_lines_at_t()
        img = self.static_explosion.lines_to_circle(img)
        return img


class Explosions:
    '''Affichage de plusieurs explosions dans une image avec OpenCV.'''

    comptage = -1

    def __init__(self):
        # La boucle d'affichage
        self.loop = 1
        # Calcul du fps
        self.t_zero = time()
        self.freq = 0
        self.img = get_black_image()

        # Lancement d'une explosion
        self.explosion_one_start()
        # Lancement d'une autre explosion
        self.explosion_two_start()

        # Lancement de la fenêtre OpenCV
        self.display()

    def update_freq(self):
        '''Calcul et affichage du fps.'''

        self.freq += 1

        if time() - self.t_zero > 1:
            self.t_zero = time()
            print("Fréquence =", self.freq)
            self.freq = 0

    def explosion_one(self, numero):
        global LINES

        n = 8
        O = 200, 400
        start = 20
        gap = 30
        ampli = 50
        pixel = 2

        # Déplacement linéaire de O sur x,y pendant 1s
        slide = 500
        # Diminution de l'amplitude par seconde
        decrease = 200

        # Création d'une explosion
        LINES[numero] = DynamicExplosion(O, n, start, gap, ampli, pixel, slide, decrease)
        LINES[numero].explosion(numero)

    def explosion_one_start(self):
        Explosions.comptage += 1
        numero = Explosions.comptage
        t1 = threading.Thread(target=self.explosion_one, args=(numero,))
        t1.start()

    def explosion_two(self, numero):
        global LINES
        n = 5
        O = 400, 300
        start = 20
        gap = 30
        ampli = 100
        pixel = 1

        # Déplacement linéaire de O sur x,y pendant 1s
        slide = 300
        # Diminution de l'amplitude par seconde
        decrease = 300

        # Création d'une explosion
        LINES[numero] = DynamicExplosion(   O, n, start, gap, ampli, pixel,
                                            slide, decrease)
        LINES[numero].explosion(numero)

    def explosion_two_start(self):
        Explosions.comptage += 1
        numero = Explosions.comptage
        t2 = threading.Thread(target=self.explosion_two, args=(numero,))
        t2.start()

    def lines_to_circles(self, img, numero):

        global LINES
        img = LINES[numero].explosion(img)
        return img

    def display(self):

        while self.loop:
            self.update_freq()

            # Recalcul de l'image avec toutes les lines
            img = get_black_image()
            key_list_to_remove = []
            for k, v in LINES.items():

                # Le coeur du calcul
                img = self.lines_to_circles(img, k)

                if v.ampli == 0:
                    print("LINES[{}] à supprimer".format(k))
                    key_list_to_remove.append(k)

            # Interdiction de supprimer une clé en cours de parcours
            for i in key_list_to_remove:
                del LINES[i]

            # StaticDisplay an image
            cv2.imshow("Ceci n'est pas une image", img)

            # wait for esc key to exit
            key = np.int16(cv2.waitKey(33))
            if key == 27:  # Echap
                break

        cv2.destroyAllWindows()


def t_s(a, b):
    return tuple(map(operator.add, a, b))

def get_droite_coeff(x1, y1, x2, y2):

    if x2 - x1 != 0:
        a = (y2 - y1) / (x2 - x1)
        b = y1 - a * x1
    else:
        a, b = None, None

    return a, b

def draw_line(img, A, B):
    '''Retourne l'image avec le dessin de la droite entre A et B.'''

    a, b = get_droite_coeff(A[0], A[1], B[0], B[1])

    for i in range(int(A[0]), int(B[0])):
        x = i
        y = int(a*x + b)
        if 0 < x < LARG and 0 < y < HAUT:
            img[y][x] = [255]

    return img

def get_line(A, B):
    '''Retourne la liste des points de cette droite'''

    a, b = get_droite_coeff(A[0], A[1], B[0], B[1])

    points = []
    for i in range(int(A[0]), int(B[0])):
        x = i
        y = int(a*x + b)
        if 0 < x < LARG and 0 < y < HAUT:
            points.append([x, y])

    return points

def test():
    ''''''

    print("Explosions")
    Explosions()


if __name__ == "__main__":
    test()
