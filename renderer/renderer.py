#!/usr/bin/env python

import sys
import time
import math
import random
import pygame
import objreader


WIDTH = 800
HEIGHT = 600
WINDOW_TITLE = "Renderer"

FPS = 60
TOTAL_TIME = 0.0
TARGET_FRAME_TIME = 1.0 / 60.0
FRAME_RATE_TIME = 0.0
FRAME_RATE_COUNT = 0
FRAME_RATE_REFRESH = 1


def cache_globals(fn):
    """
    Decorator to cache global lookups as constants.
    """
    from byteplay import Code, LOAD_CONST, LOAD_GLOBAL, LOAD_ATTR
    code = Code.from_code(fn.func_code)

    missing = object()
    program_counter = 0
    while program_counter < len(code.code):
        opcode, arg = code.code[program_counter]

        if opcode == LOAD_GLOBAL:
            const = fn.func_globals.get(arg, missing)
            if const is not missing:
                code.code[program_counter] = (LOAD_CONST, const)

        elif opcode == LOAD_ATTR:
            prev_opcode, prev_arg = code.code[program_counter-1]
            const = getattr(prev_arg, arg, missing)
            if const is not missing:
                code.code[program_counter-1:program_counter+1] = [(LOAD_CONST, const)]
                program_counter -= 1

        program_counter += 1

    fn.func_code = code.to_code()
    return fn


class Scene(object):
    """
    The rendered scene.
    """

    def __init__(self, surface, width, height):
        """
        Initialize variables that define scene properties.
        """
        # PyGame surface handle
        self.surface = surface
        self.font = pygame.font.SysFont("Arial", 12)

        # Basic scene geometry
        self.width = width
        self.height = height
        self.centre_x = self.width / 2
        self.centre_y = self.height / 2

        # Camera attributes
        self.camera_position = [0, 0, -10]
        self.camera_rotation = [0, 0, 0]
        self.camera_distortion = 512
        self.light_source = [0.7, 0.7, -0.7]
        self.rotating = False

        # Mesh attributes
        self.point_colour = (0, 0, 0)
        self.line_colour = (50, 50, 50)
        self.facet_colour = (100, 255, 100)
        self.filled = False

        # Model (default model is cube)
        self.vertices = ((-1, -1, 1), (-1, 1, 1),
                         (1, 1, 1), (1, -1, 1),
                         (-1, -1, -1), (-1, 1, -1),
                         (1, 1, -1), (1, -1, -1))

        self.facets = ((0, 1, 2), (2, 3, 0), (1, 5, 6), (6, 2, 1),
                       (5, 4, 7), (7, 6, 5), (4, 0, 3), (3, 7, 4),
                       (3, 2, 6), (6, 7, 3), (0, 5, 1), (0, 4, 5))

        self.edges = ((0, 1), (1, 2), (2, 3), (3, 0),
                      (4, 5), (5, 6), (6, 7), (7, 4),
                      (0, 4), (1, 5), (2, 6), (3, 7))

    def load_model(self, vertices, facets, edges):
        """
        Load a new model definition.
        """
        self.vertices = vertices
        self.facets = facets
        self.edges = edges

    @cache_globals
    def render_scene(self):
        """
        Render the scene.
        """
        self.render_background()
        self.render_fps()
        self.render_model()
        pygame.display.flip()

    @cache_globals
    def render_background(self):
        """
        Render a checkered background.
        """
        dark_colour = (175, 175, 175)
        light_colour = (235, 235, 235)
        square_size = 32

        x = 0
        while x < WIDTH:
            y = 0
            while y < HEIGHT:
                if (x / square_size) % 2 != (y / square_size) % 2:
                    colour = dark_colour
                else:
                    colour = light_colour

                pygame.draw.polygon(
                    self.surface, colour,
                    ((x, y), (x+square_size, y), (x+square_size, y+square_size), (x, y+square_size)), 0)
                y += square_size

            x += square_size

    def render_fps(self):
        """
        Draw the FPS count on the top left of the screen.
        """
        text = self.font.render(str(FPS), True, (0, 0, 0))
        self.surface.blit(text, (8, 8))

    @cache_globals
    def render_model(self):
        """
        Render the rotating cube.
        """
        # Rotate the camera if the ROTATING flag is set
        if self.rotating:
            self.camera_rotation[0] += 0.02
            self.camera_rotation[1] += 0.02
            self.camera_rotation[2] += 0.02

        # Store rotated points for vertex drawing
        num_vertices = len(self.vertices)
        point_list = [None] * num_vertices
        depth_list = [None] * num_vertices

        # Project all the points.
        for i in range(num_vertices):
            # Apply rotation for each axis
            x = self.vertices[i][0]
            y = self.vertices[i][1]
            z = self.vertices[i][2]

            tmp = z
            z = -x * math.sin(self.camera_rotation[0]) - z * math.cos(self.camera_rotation[0])
            x = -x * math.cos(self.camera_rotation[0]) + tmp * math.sin(self.camera_rotation[0])

            tmp = z
            z = -y * math.sin(self.camera_rotation[1]) + z * math.cos(self.camera_rotation[1])
            y = y * math.cos(self.camera_rotation[1]) + tmp * math.sin(self.camera_rotation[1])

            tmp = x
            x = x * math.cos(self.camera_rotation[2]) - y * math.sin(self.camera_rotation[2])
            y = y * math.cos(self.camera_rotation[2]) + tmp * math.sin(self.camera_rotation[2])

            x -= self.camera_position[0]
            y -= self.camera_position[1]
            z -= self.camera_position[2]

            # Guard against divide by zero
            if z == 0:
                z = 0.00001

            # Do projection transform
            screen_x = self.camera_distortion * x / z
            screen_y = self.camera_distortion * y / z

            screen_x += self.centre_x
            screen_y += self.centre_y

            screen_x = int(screen_x)
            screen_y = int(screen_y)

            point_list[i] = (screen_x, screen_y)
            depth_list[i] = z

        # draw each facet in the scene.
        num_facets = len(self.facets)

        if self.filled:
            ordered_facets = self.painters_algorithm(depth_list, self.facets)

            for i in range(num_facets):
                point1 = point_list[ordered_facets[i][0]]
                point2 = point_list[ordered_facets[i][1]]
                point3 = point_list[ordered_facets[i][2]]

                colour = self.gouraud_shading(self.vertices[ordered_facets[i][0]],
                                              self.vertices[ordered_facets[i][1]],
                                              self.vertices[ordered_facets[i][2]],
                                              self.facet_colour)

                self.render_fill_triangle(
                    point1[0], point1[1], point2[0], point2[1], point3[0], point3[1], colour)

        else:
            for i in range(num_facets):
                point1 = point_list[self.facets[i][0]]
                point2 = point_list[self.facets[i][1]]
                point3 = point_list[self.facets[i][2]]

                self.render_triangle(
                    point1[0], point1[1], point2[0], point2[1], point3[0], point3[1])

    @staticmethod
    def painters_algorithm(depths, facets):
        """
        Given a list of vertex depths and facets, return
        a list of facets in reverse order of the average
        depth of the vertices that make up the facet.
        """
        avg_depth = lambda facet: sum([depths[x] for x in facet[:3]]) / 3.0
        return sorted(facets, key=avg_depth, reverse=True)

    @cache_globals
    def gouraud_shading(self, a, b, c, colour):
        """
        Calculate the colour of a facet by figuring out the angle
        at which the ambient light source hits it.
        """
        vector_ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
        vector_ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])

        # Length normalize the vectors
        length_ab = math.sqrt(sum([x**2 for x in vector_ab]))
        length_ac = math.sqrt(sum([x**2 for x in vector_ac]))
        vector_ab = [x/length_ab for x in vector_ab]
        vector_ac = [x/length_ac for x in vector_ac]

        # Compute the surface normal
        surface_normal = (vector_ab[1] * vector_ac[2] - vector_ab[2] * vector_ac[1],
                          vector_ab[2] * vector_ac[0] - vector_ab[0] * vector_ac[2],
                          vector_ab[0] * vector_ac[1] - vector_ab[1] * vector_ac[0])

        # find the angle at which the light hits the surface
        angle = self.light_source[0] * surface_normal[0] + \
            self.light_source[1] * surface_normal[1] + \
            self.light_source[2] * surface_normal[2]

        # Guard against domain error
        if angle > 1:
            angle = 1
        elif angle < -1:
            angle = -1

        angle = math.acos(angle) / math.pi

        # Change colour based on factor
        shade = (math.floor(colour[0] * angle),
                 math.floor(colour[1] * angle),
                 math.floor(colour[2] * angle))

        return shade

    # Functions for drawing graphics primitives.
    @cache_globals
    def render_point(self, x, y):
        """
        Render a single pixel
        """
        pygame.draw.circle(self.surface, self.point_colour, (x, y), 2)

    @cache_globals
    def render_line(self, x1, y1, x2, y2):
        """
        Render a line.
        """
        pygame.draw.line(self.surface, self.line_colour, (x1, y1), (x2, y2))

    @cache_globals
    def render_triangle(self, x1, y1, x2, y2, x3, y3):
        """
        Render an unfilled triangle.
        """
        pygame.draw.polygon(self.surface, self.line_colour, ((x1, y1), (x2, y2), (x3, y3)), 1)

    @cache_globals
    def render_fill_triangle(self, x1, y1, x2, y2, x3, y3, colour):
        """
        Render a filled triangle.
        """
        pygame.draw.polygon(self.surface, colour, ((x1, y1), (x2, y2), (x3, y3)), 0)


def render_loop(scene):
    """
    Control sleep between frames to hit FPS target.
    """
    global TOTAL_TIME
    global FPS
    global FRAME_RATE_TIME
    global FRAME_RATE_COUNT
    global FRAME_RATE_REFRESH

    start_time = time.time()
    scene.render_scene()
    end_time = time.time()

    # Figure out how long it took to render the frame.
    time_elapsed = end_time - start_time
    sleep_time = TARGET_FRAME_TIME - time_elapsed

    # If sleep time is negative, the frame took too
    # long so don't sleep this time.
    if sleep_time < 0:
        sleep_time = 0.0

    # Find the time to execute the frame
    # and add it to the frame rate time.
    cycle_time = time_elapsed + sleep_time
    FRAME_RATE_TIME += cycle_time

    # If a frame rate refresh is overdue, update it.
    if FRAME_RATE_TIME >= FRAME_RATE_REFRESH:
        FPS = int(FRAME_RATE_COUNT / FRAME_RATE_REFRESH)

        FRAME_RATE_TIME = 0.0
        FRAME_RATE_COUNT = 0

    FRAME_RATE_COUNT += 1

    TOTAL_TIME += cycle_time
    time.sleep(sleep_time)


def handle_mouse_event(event, scene):
    """
    Handle various types of mouse input.
    """
    # Zooming in and out.
    if event.button == 4:
        if scene.camera_position[2] < 0:
            scene.camera_position[2] += 1
    if event.button == 5:
        scene.camera_position[2] -= 1


def handle_key_event(event, scene):
    """
    Reset the camera position and rotation with the keyboard.
    """
    if event.key == pygame.K_r:
        scene.rotating = not scene.rotating

    if event.key == pygame.K_f:
        scene.filled = not scene.filled

    if event.key == pygame.K_b:
        scene.camera_position[2] = -10

        scene.camera_rotation[0] = 0.0
        scene.camera_rotation[1] = 0.0
        scene.camera_rotation[2] = 0.0


def handle_mouse_motion(scene):
    """
    Control pitch, yaw and roll with the mouse.
    """
    # If the left mouse button is pressed, handle pitch and yaw.
    if pygame.mouse.get_pressed()[0]:
        relative_movement = pygame.mouse.get_rel()
        scene.camera_rotation[0] += relative_movement[0] * 0.02
        scene.camera_rotation[1] += relative_movement[1] * 0.02

    if pygame.mouse.get_pressed()[2]:
        relative_movement = pygame.mouse.get_rel()
        scene.camera_rotation[2] += relative_movement[0] * 0.02


def colorize_facets(facets):
    """
    Assign a random colour to each facets in a list.
    """
    for i in range(len(facets)):
        facets[i].append((random.randrange(256), random.randrange(256), random.randrange(256)))

    return facets


@cache_globals
def main():
    """
    The main render loop.
    """
    # Initialize PyGame
    pygame.init()
    pygame.display.set_caption(WINDOW_TITLE)
    surface = pygame.display.set_mode((WIDTH, HEIGHT))

    # Create scene
    scene = Scene(surface, WIDTH, HEIGHT)

    # Read the model file if provided
    if len(sys.argv) == 2:
        vertices, facets, edges = objreader.read(sys.argv[1])
        facets = colorize_facets(facets)
        scene.load_model(vertices, facets, edges)

    # Kick off the rendering loop
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                handle_key_event(event, scene)
            if event.type == pygame.MOUSEBUTTONDOWN:
                handle_mouse_event(event, scene)
            if event.type == pygame.MOUSEMOTION:
                handle_mouse_motion(scene)

        render_loop(scene)


if __name__ == "__main__":
    main()
